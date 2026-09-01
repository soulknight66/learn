from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .db import Database
from .scoring import DEFAULT_WEIGHTS, priority_score
from .util import canonical_json, json_value, slugify, tree_sha256


class CatalogSynthesisError(RuntimeError):
    """The normalized catalog cannot produce a trustworthy synthesis artifact."""


@dataclass(frozen=True)
class CatalogSynthesisResult:
    evidence: dict[str, Any]
    validators: list[dict[str, Any]]
    artifact_type: str
    semantic_path: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class CatalogDocuments:
    backlog: dict[str, Any]
    concept_map: dict[str, Any]
    provenance: dict[str, Any]
    backlog_markdown: str
    concept_markdown: str
    readme: str


_FAMILY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("distributed-systems", ("distributed", "consensus", "replication", "分布式")),
    ("storage-database", ("database", "storage", "indexing", "数据库", "b+ tree", "lsm")),
    ("operating-systems", ("operating system", "virtual memory", "filesystem", "操作系统")),
    ("networking", ("network", "socket", "http", "dns", "bittorrent", "计算机网络")),
    ("languages-compilers", ("compiler", "programming language", "interpreter", "编译", "语言设计")),
    ("security", ("security", "cryptography", "系统安全", "安全")),
    ("software-engineering", ("software engineering", "软件工程", "testing", "maintenance")),
    ("architecture", ("processor", "architecture", "体系结构", "digital logic", "emulator")),
    ("web-services", ("web server", "web development", "web应用", "web开发", "api")),
    ("machine-learning", ("machine learning", "neural", "deep learning", "人工智能", "机器学习")),
    ("foundations", ("algorithm", "data structure", "mathematics", "编程入门", "数学", "数据结构")),
)

_FAMILY_PROFILE: dict[str, tuple[float, float, float, float]] = {
    # systems depth, production relevance, prerequisite value, artifact uniqueness
    "distributed-systems": (9.5, 9.0, 8.5, 8.5),
    "storage-database": (9.0, 9.0, 8.0, 8.0),
    "operating-systems": (10.0, 8.0, 9.0, 8.5),
    "networking": (8.5, 9.0, 8.5, 8.0),
    "languages-compilers": (8.5, 7.0, 7.5, 8.5),
    "security": (8.0, 9.0, 7.5, 8.0),
    "software-engineering": (6.0, 10.0, 9.0, 7.0),
    "architecture": (9.0, 7.0, 8.5, 8.0),
    "web-services": (5.5, 9.5, 7.0, 6.5),
    "machine-learning": (5.0, 7.0, 6.0, 6.0),
    "foundations": (4.5, 6.0, 10.0, 5.0),
    "general": (5.0, 6.0, 5.0, 5.0),
}

_FORMAT_AVAILABILITY = {
    "repository": 9.0,
    "article": 8.0,
    "pdf": 7.5,
    "video": 6.0,
}

_COMPONENT_DERIVATION = {
    "expected_future_learning_value": "blend of difficulty, systems depth, production relevance, and curriculum importance",
    "future_regeneration_cost": "record richness, difficulty, and high-value family/tier heuristic",
    "production_relevance": "normalized source value where present plus a documented family prior",
    "systems_depth": "documented family prior inferred from topic, category, and concepts",
    "curriculum_importance": "course unit/edge connectivity or Build-Your-Own-X priority tier",
    "source_availability": "course resource availability or linked tutorial format",
    "prerequisite_value": "curriculum out-degree plus documented family prior",
    "artifact_uniqueness": "family prior plus record/concept richness",
    "agent_compute_cost": "difficulty and estimated implementation/study scope; negative default weight",
}


def _clamp(value: float, low: float = 0.0, high: float = 10.0) -> float:
    return round(max(low, min(high, float(value))), 4)


def _finite_number(value: object, default: float) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _family(*values: object) -> str:
    text = " ".join(str(value or "") for value in values).casefold()
    for family, needles in _FAMILY_RULES:
        if any(needle in text for needle in needles):
            return family
    return "general"


def _labels(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for raw in value:
        if raw is None:
            continue
        label = re.sub(r"\s+", " ", str(raw)).strip()
        key = label.casefold()
        if label and key not in seen:
            seen.add(key)
            result.append(label)
    return result


def _language_labels(metadata: dict[str, Any], fallback: object = None) -> list[str]:
    explicit = _labels(metadata.get("languages"))
    if explicit:
        return explicit
    raw = str(metadata.get("programming_languages_raw") or fallback or "")
    return [piece.strip() for piece in re.split(r"\s*(?:,|/)\s*", raw) if piece.strip()]


def _selected_weights(raw: object) -> dict[str, float]:
    selected = {name: float(value) for name, value in DEFAULT_WEIGHTS.items()}
    if raw is None:
        return selected
    if not isinstance(raw, Mapping):
        raise CatalogSynthesisError("weights must be an object")
    unknown = sorted(set(str(name) for name in raw) - set(DEFAULT_WEIGHTS))
    if unknown:
        raise CatalogSynthesisError(f"unknown priority weights: {', '.join(unknown)}")
    for name, value in raw.items():
        number = _finite_number(value, math.nan)
        if not math.isfinite(number) or abs(number) > 100:
            raise CatalogSynthesisError(f"invalid priority weight for {name}")
        selected[str(name)] = number
    return dict(sorted(selected.items()))


def _selected_overrides(raw: object) -> dict[str, float]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise CatalogSynthesisError("manual_overrides must be an object")
    selected: dict[str, float] = {}
    for identifier, value in raw.items():
        name = str(identifier).strip()
        number = _finite_number(value, math.nan)
        if not name or not math.isfinite(number) or abs(number) > 100:
            raise CatalogSynthesisError(f"invalid manual priority override: {identifier!r}")
        if number:
            selected[name] = round(number, 4)
    return dict(sorted(selected.items()))


def _source_provenance(source: dict[str, Any]) -> dict[str, Any]:
    metadata = json_value(source.get("metadata_json"), {})
    return {
        "source_id": source["source_id"],
        "type": source["type"],
        "name": source["name"],
        "path": source["path"],
        "upstream_url": source["upstream_url"],
        "commit_hash": source["commit_hash"],
        "license": source["license"] or "NOASSERTION",
        "adapter": metadata.get("adapter"),
        "extractor_version": metadata.get("extractor_version"),
        "tree_hash": metadata.get("tree_hash"),
        "classification": "source-derived",
    }


def _load_catalog(db: Database) -> dict[str, Any]:
    # All normalized tables belong to one catalog snapshot.  A deferred read
    # transaction prevents a concurrent source activation from mixing commits.
    with db.transaction() as connection:
        sources = [
            dict(row)
            for row in connection.execute(
                """
                SELECT source_id,type,name,path,upstream_url,commit_hash,license,metadata_json
                FROM sources WHERE is_active=1 ORDER BY source_id
                """
            )
        ]
        courses = [
            dict(row)
            for row in connection.execute(
                """
                SELECT c.course_id,c.source_id,c.slug,c.institution,c.title,c.topic,
                       c.description,c.prerequisites_json,c.estimated_human_hours,
                       c.difficulty,c.source_metadata_json,c.status
                FROM courses AS c
                JOIN sources AS s ON s.source_id=c.source_id
                WHERE s.is_active=1
                ORDER BY c.course_id
                """
            )
        ]
        projects = [
            dict(row)
            for row in connection.execute(
                """
                SELECT p.project_id,p.source_id,p.slug,p.title,p.category,
                       p.implementation_language,p.upstream_reference,p.concepts_json,
                       p.difficulty,p.production_relevance,p.source_format,
                       p.priority_tier,p.metadata_json
                FROM build_projects AS p
                JOIN sources AS s ON s.source_id=p.source_id
                WHERE s.is_active=1
                ORDER BY p.project_id
                """
            )
        ]
        units = [
            dict(row)
            for row in connection.execute(
                """
                SELECT u.unit_id,u.course_id,u.type,u.unit_order,u.title,
                       u.source_reference,u.metadata_json
                FROM course_units AS u
                JOIN courses AS c ON c.course_id=u.course_id
                JOIN sources AS s ON s.source_id=c.source_id
                WHERE s.is_active=1
                ORDER BY u.course_id,u.unit_order,u.unit_id
                """
            )
        ]
        edges = [
            dict(row)
            for row in connection.execute(
                """
                SELECT e.from_course_id,e.to_course_id,e.relation,e.evidence,e.inferred
                FROM curriculum_edges AS e
                JOIN courses AS from_course ON from_course.course_id=e.from_course_id
                JOIN sources AS from_source ON from_source.source_id=from_course.source_id
                JOIN courses AS to_course ON to_course.course_id=e.to_course_id
                JOIN sources AS to_source ON to_source.source_id=to_course.source_id
                WHERE from_source.is_active=1 AND to_source.is_active=1
                ORDER BY e.from_course_id,e.to_course_id,e.relation
                """
            )
        ]
    if not courses or not projects:
        raise CatalogSynthesisError(
            "catalog synthesis requires at least one normalized course and project"
        )
    source_ids = {source["source_id"] for source in sources}
    missing = sorted(
        {record["source_id"] for record in [*courses, *projects]} - source_ids
    )
    if missing:
        raise CatalogSynthesisError(f"catalog records reference missing sources: {missing}")
    return {
        "sources": sources,
        "courses": courses,
        "projects": projects,
        "units": units,
        "edges": edges,
    }


def _catalog_fingerprint(catalog: dict[str, Any]) -> str:
    stable_sources = []
    for source in catalog["sources"]:
        metadata = json_value(source.get("metadata_json"), {})
        stable_sources.append(
            {
                key: source[key]
                for key in (
                    "source_id",
                    "type",
                    "name",
                    "path",
                    "upstream_url",
                    "commit_hash",
                    "license",
                )
            }
            | {
                "adapter": metadata.get("adapter"),
                "extractor_version": metadata.get("extractor_version"),
                "tree_hash": metadata.get("tree_hash"),
            }
        )
    material = {
        "sources": stable_sources,
        "courses": catalog["courses"],
        "projects": catalog["projects"],
        "units": catalog["units"],
        "edges": catalog["edges"],
    }
    return hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()


def _course_components(
    course: dict[str, Any],
    family: str,
    units: list[dict[str, Any]],
    incoming: int,
    outgoing: int,
) -> dict[str, float]:
    difficulty = _clamp(_finite_number(course["difficulty"], 5.0))
    systems, production, prerequisite_prior, uniqueness_prior = _FAMILY_PROFILE[family]
    resource_values: list[float] = []
    for unit in units:
        availability = str(json_value(unit["metadata_json"], {}).get("availability", ""))
        resource_values.append(
            {"LINKED": 10.0, "DESCRIBED": 6.0, "UNAVAILABLE": 0.0}.get(
                availability, 4.0
            )
        )
    availability = (
        sum(resource_values) / len(resource_values) if resource_values else 3.0
    )
    connectivity = incoming + outgoing
    curriculum = _clamp(4.0 + math.log2(len(units) + 1) + min(3.0, connectivity * 0.6))
    expected_value = _clamp(
        (difficulty + systems + production + curriculum) / 4.0 + 0.8
    )
    hours = _finite_number(course["estimated_human_hours"], 40.0)
    return {
        "expected_future_learning_value": expected_value,
        "future_regeneration_cost": _clamp(
            3.5 + difficulty * 0.35 + min(2.5, len(units) * 0.18)
        ),
        "production_relevance": _clamp(production),
        "systems_depth": _clamp(systems),
        "curriculum_importance": curriculum,
        "source_availability": _clamp(availability),
        "prerequisite_value": _clamp(
            prerequisite_prior * 0.7 + min(3.0, outgoing * 0.8)
        ),
        "artifact_uniqueness": _clamp(
            uniqueness_prior + min(1.5, len(units) * 0.08)
        ),
        "agent_compute_cost": _clamp(difficulty * 0.65 + min(3.5, hours / 60.0)),
    }


def _project_components(project: dict[str, Any], family: str, concept_count: int) -> dict[str, float]:
    difficulty = _clamp(_finite_number(project["difficulty"], 5.0))
    systems, production_prior, prerequisite_prior, uniqueness_prior = _FAMILY_PROFILE[family]
    production = _clamp(
        _finite_number(project["production_relevance"], production_prior)
    )
    tier = max(1, min(3, int(_finite_number(project["priority_tier"], 3.0))))
    curriculum = {1: 9.0, 2: 7.0, 3: 5.0}[tier]
    availability = _FORMAT_AVAILABILITY.get(str(project["source_format"]), 6.0)
    expected_value = _clamp(
        (difficulty + systems + production + curriculum) / 4.0 + 0.7
    )
    return {
        "expected_future_learning_value": expected_value,
        "future_regeneration_cost": _clamp(
            5.0 + (4 - tier) * 0.8 + difficulty * 0.25 + min(1.0, concept_count * 0.15)
        ),
        "production_relevance": production,
        "systems_depth": _clamp(systems),
        "curriculum_importance": curriculum,
        "source_availability": _clamp(availability),
        "prerequisite_value": _clamp(prerequisite_prior),
        "artifact_uniqueness": _clamp(
            uniqueness_prior + min(1.5, concept_count * 0.2)
        ),
        "agent_compute_cost": _clamp(difficulty * 0.8 + (4 - tier) * 0.6),
    }


def _score_item(
    item: dict[str, Any],
    components: dict[str, float],
    weights: dict[str, float],
    overrides: dict[str, float],
) -> dict[str, Any]:
    identifier = item["record_id"]
    override = overrides.get(identifier, 0.0)
    base = priority_score(components, weights)
    return item | {
        "score": round(base + override, 4),
        "base_score": base,
        "manual_priority_delta": override,
        "score_components": dict(sorted(components.items())),
        "score_classification": "inferred-deterministic",
    }


def _build_items(
    catalog: dict[str, Any], weights: dict[str, float], overrides: dict[str, float]
) -> list[dict[str, Any]]:
    sources = {source["source_id"]: source for source in catalog["sources"]}
    units_by_course: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in catalog["units"]:
        units_by_course[unit["course_id"]].append(unit)
    incoming: Counter[str] = Counter()
    outgoing: Counter[str] = Counter()
    for edge in catalog["edges"]:
        outgoing[edge["from_course_id"]] += 1
        incoming[edge["to_course_id"]] += 1

    items: list[dict[str, Any]] = []
    for course in catalog["courses"]:
        metadata = json_value(course["source_metadata_json"], {})
        prerequisites = _labels(json_value(course["prerequisites_json"], []))
        family = _family(course["topic"], course["title"], course["description"])
        concept_labels = _labels([family.replace("-", " "), course["topic"], *prerequisites])
        source = sources[course["source_id"]]
        provenance = metadata.get("provenance", {})
        course_units = units_by_course[course["course_id"]]
        item = {
            "record_id": course["course_id"],
            "kind": "course",
            "slug": course["slug"],
            "title": course["title"],
            "family": family,
            "topic": course["topic"],
            "institution": course["institution"],
            "languages": _language_labels(metadata),
            "concepts": concept_labels,
            "concept_ids": [slugify(label.casefold()) for label in concept_labels],
            "difficulty": _finite_number(course["difficulty"], 5.0),
            "estimated_human_hours": _finite_number(
                course["estimated_human_hours"], 40.0
            ),
            "source_availability": dict(Counter(unit["type"] for unit in course_units)),
            "provenance": {
                "classification": "source-derived",
                "source_id": source["source_id"],
                "source_name": source["name"],
                "source_path": source["path"],
                "upstream_url": source["upstream_url"],
                "source_commit": source["commit_hash"],
                "source_license": source["license"] or "NOASSERTION",
                "source_reference": provenance.get("source_file"),
                "content_sha256": provenance.get("content_sha256"),
            },
        }
        items.append(
            _score_item(
                item,
                _course_components(
                    course,
                    family,
                    course_units,
                    incoming[course["course_id"]],
                    outgoing[course["course_id"]],
                ),
                weights,
                overrides,
            )
        )

    for project in catalog["projects"]:
        metadata = json_value(project["metadata_json"], {})
        source = sources[project["source_id"]]
        project_concepts = _labels(json_value(project["concepts_json"], []))
        family = _family(project["category"], project["title"], *project_concepts)
        concept_labels = _labels(
            [family.replace("-", " "), project["category"], *project_concepts]
        )
        provenance = metadata.get("provenance", {})
        item = {
            "record_id": project["project_id"],
            "kind": "build-project",
            "slug": project["slug"],
            "title": project["title"],
            "family": family,
            "topic": project["category"],
            "institution": None,
            "languages": _language_labels(metadata, project["implementation_language"]),
            "concepts": concept_labels,
            "concept_ids": [slugify(label.casefold()) for label in concept_labels],
            "difficulty": _finite_number(project["difficulty"], 5.0),
            "estimated_human_hours": round(
                4.0 + _finite_number(project["difficulty"], 5.0) * 1.5, 1
            ),
            "source_availability": {
                "format": project["source_format"],
                "upstream_reference": project["upstream_reference"],
            },
            "provenance": {
                "classification": "source-derived catalog entry",
                "source_id": source["source_id"],
                "source_name": source["name"],
                "source_path": source["path"],
                "upstream_url": source["upstream_url"],
                "source_commit": source["commit_hash"],
                "source_license": source["license"] or "NOASSERTION",
                "source_reference": project["upstream_reference"],
                "content_sha256": provenance.get("content_sha256"),
                "linked_resource_license": metadata.get(
                    "linked_resource_license", "NOASSERTION"
                ),
            },
        }
        items.append(
            _score_item(
                item,
                _project_components(project, family, len(project_concepts)),
                weights,
                overrides,
            )
        )

    identifiers = {item["record_id"] for item in items}
    unknown_overrides = sorted(set(overrides) - identifiers)
    if unknown_overrides:
        raise CatalogSynthesisError(
            f"manual overrides reference unknown records: {', '.join(unknown_overrides)}"
        )
    items.sort(
        key=lambda item: (
            -item["score"],
            item["kind"],
            item["title"].casefold(),
            item["record_id"],
        )
    )
    for rank, item in enumerate(items, 1):
        item["rank"] = rank
    return items


def _build_concept_map(items: list[dict[str, Any]], fingerprint: str) -> dict[str, Any]:
    labels: dict[str, str] = {}
    memberships: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {"courses": [], "projects": []}
    )
    cooccurrence: Counter[tuple[str, str]] = Counter()
    rank_by_id = {item["record_id"]: item["rank"] for item in items}
    for item in items:
        unique_ids: list[str] = []
        for identifier, label in zip(item["concept_ids"], item["concepts"]):
            labels.setdefault(identifier, label)
            if identifier in unique_ids:
                continue
            unique_ids.append(identifier)
            bucket = "courses" if item["kind"] == "course" else "projects"
            memberships[identifier][bucket].append(item["record_id"])
        ordered_ids = sorted(unique_ids)
        for index, left in enumerate(ordered_ids):
            for right in ordered_ids[index + 1 :]:
                cooccurrence[(left, right)] += 1

    nodes = []
    for concept_id in sorted(memberships):
        courses = sorted(memberships[concept_id]["courses"], key=rank_by_id.get)
        projects = sorted(memberships[concept_id]["projects"], key=rank_by_id.get)
        combined = sorted([*courses, *projects], key=rank_by_id.get)
        nodes.append(
            {
                "concept_id": concept_id,
                "label": labels[concept_id],
                "course_ids": courses,
                "project_ids": projects,
                "item_count": len(combined),
                "top_backlog_ids": combined[:10],
                "classification": "inferred-index",
            }
        )
    edges = [
        {
            "from": left,
            "to": right,
            "relation": "co-occurs-in-catalog-record",
            "weight": weight,
            "classification": "inferred",
        }
        for (left, right), weight in sorted(cooccurrence.items())
    ]
    return {
        "schema_version": 1,
        "catalog_snapshot_sha256": fingerprint,
        "method": "normalized concept membership and within-record co-occurrence",
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "concepts": len(nodes),
            "relations": len(edges),
            "course_memberships": sum(len(node["course_ids"]) for node in nodes),
            "project_memberships": sum(len(node["project_ids"]) for node in nodes),
        },
    }


def _markdown_cell(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).replace("|", "\\|").strip()


def _backlog_markdown(backlog: dict[str, Any]) -> str:
    lines = [
        "# Deterministic learning backlog",
        "",
        (
            f"This backlog ranks {backlog['summary']['total_items']} normalized records "
            f"({backlog['summary']['courses']} courses and "
            f"{backlog['summary']['projects']} build projects). Scores are inferred planning "
            "signals, not correctness or course-quality grades."
        ),
        "",
        f"Catalog snapshot: `{backlog['catalog_snapshot_sha256']}`.",
        "",
        "| Rank | Score | Type | Family | Title | Source record |",
        "|---:|---:|---|---|---|---|",
    ]
    for item in backlog["items"]:
        lines.append(
            f"| {item['rank']} | {item['score']:.4f} | {_markdown_cell(item['kind'])} | "
            f"{_markdown_cell(item['family'])} | {_markdown_cell(item['title'])} | "
            f"`{item['record_id']}` |"
        )
    lines.extend(
        [
            "",
            "## Scoring boundary",
            "",
            "Every component and weight is present in `BACKLOG.json`; manual changes are explicit "
            "deltas. The deterministic validator recomputes this file from authoritative SQLite state.",
            "",
        ]
    )
    return "\n".join(lines)


def _concept_markdown(concept_map: dict[str, Any], items: list[dict[str, Any]]) -> str:
    title_by_id = {item["record_id"]: item["title"] for item in items}
    ordered = sorted(
        concept_map["nodes"],
        key=lambda node: (-node["item_count"], node["label"].casefold(), node["concept_id"]),
    )
    lines = [
        "# Catalog concept map",
        "",
        "Concept membership and relations are inferred from normalized topics, categories, "
        "prerequisites, and project concepts. They are navigation aids, not claims of mastery.",
        "",
        "| Concept | Courses | Projects | Highest-priority examples |",
        "|---|---:|---:|---|",
    ]
    for node in ordered:
        examples = "; ".join(
            _markdown_cell(title_by_id[identifier])
            for identifier in node["top_backlog_ids"][:3]
        )
        lines.append(
            f"| {_markdown_cell(node['label'])} (`{node['concept_id']}`) | "
            f"{len(node['course_ids'])} | {len(node['project_ids'])} | {examples} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_catalog_documents(
    db: Database,
    *,
    weights: Mapping[str, float] | None = None,
    manual_overrides: Mapping[str, float] | None = None,
) -> CatalogDocuments:
    selected_weights = _selected_weights(weights)
    selected_overrides = _selected_overrides(manual_overrides)
    catalog = _load_catalog(db)
    fingerprint = _catalog_fingerprint(catalog)
    items = _build_items(catalog, selected_weights, selected_overrides)
    sources = [_source_provenance(source) for source in catalog["sources"]]
    family_counts = dict(sorted(Counter(item["family"] for item in items).items()))
    backlog = {
        "schema_version": 1,
        "catalog_snapshot_sha256": fingerprint,
        "policy": {
            "name": "learning-value-priority-v1",
            "weights": selected_weights,
            "manual_overrides": selected_overrides,
            "component_derivation": _COMPONENT_DERIVATION,
            "tie_break": ["score descending", "kind", "title casefolded", "record_id"],
        },
        "summary": {
            "sources": len(sources),
            "courses": len(catalog["courses"]),
            "projects": len(catalog["projects"]),
            "total_items": len(items),
            "families": family_counts,
        },
        "items": items,
    }
    concept_map = _build_concept_map(items, fingerprint)
    provenance = {
        "schema_version": 1,
        "catalog_snapshot_sha256": fingerprint,
        "sources": sources,
        "derivations": {
            "catalog_records": "source-derived normalized SQLite records",
            "priority_scores": "inferred-deterministic using the embedded policy",
            "concept_membership": "inferred-deterministic from normalized metadata",
            "benchmark_or_performance_claims": False,
            "pedagogical_review_claims": False,
        },
    }
    readme = "\n".join(
        [
            "# Catalog synthesis v1",
            "",
            "This deterministic artifact turns the normalized source catalogs into a complete "
            "priority backlog and a cross-source concept index.",
            "",
            "- `BACKLOG.md` is the human-readable complete ranking.",
            "- `BACKLOG.json` contains every score component, weight, and provenance record.",
            "- `CONCEPT_MAP.md` is the human-readable concept index.",
            "- `CONCEPT_MAP.json` contains memberships and inferred co-occurrence edges.",
            "- `PROVENANCE.json` distinguishes source-derived and inferred material.",
            "",
            "Validation replays generation against authoritative SQLite state. A passing `TESTED` "
            "claim covers deterministic completeness and internal consistency only; it does not "
            "mean the rankings received independent pedagogical review.",
            "",
        ]
    )
    return CatalogDocuments(
        backlog,
        concept_map,
        provenance,
        _backlog_markdown(backlog),
        _concept_markdown(concept_map, items),
        readme,
    )


def _write_text(workspace: Path, name: str, content: str) -> None:
    target = workspace / name
    if target.is_symlink():
        raise CatalogSynthesisError(f"refusing to replace workspace symlink: {name}")
    target.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")


def _write_json(workspace: Path, name: str, value: object) -> None:
    _write_text(
        workspace,
        name,
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False),
    )


def _object_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def generate_catalog_synthesis(
    workspace: Path, payload: dict[str, Any], db: Database
) -> CatalogSynthesisResult:
    if not workspace.is_dir() or workspace.is_symlink():
        raise CatalogSynthesisError("catalog synthesis workspace must be a real directory")
    documents = build_catalog_documents(
        db,
        weights=payload.get("weights"),
        manual_overrides=payload.get("manual_overrides"),
    )
    _write_json(workspace, "BACKLOG.json", documents.backlog)
    _write_text(workspace, "BACKLOG.md", documents.backlog_markdown)
    _write_json(workspace, "CONCEPT_MAP.json", documents.concept_map)
    _write_text(workspace, "CONCEPT_MAP.md", documents.concept_markdown)
    _write_json(workspace, "PROVENANCE.json", documents.provenance)
    _write_text(workspace, "README.md", documents.readme)

    source_root = Path(__file__).resolve().parents[1]
    policy_sha256 = _object_sha256(documents.backlog["policy"])
    validators: list[dict[str, Any]] = [
        {
            "type": "required_paths",
            "name": "catalog-synthesis-layout",
            "paths": [
                "README.md",
                "BACKLOG.json",
                "BACKLOG.md",
                "CONCEPT_MAP.json",
                "CONCEPT_MAP.md",
                "PROVENANCE.json",
            ],
        },
        {
            "type": "json_fields",
            "name": "backlog-machine-schema",
            "path": "BACKLOG.json",
            "required": [
                "schema_version",
                "catalog_snapshot_sha256",
                "policy",
                "summary",
                "items",
            ],
        },
        {
            "type": "json_fields",
            "name": "concept-map-machine-schema",
            "path": "CONCEPT_MAP.json",
            "required": [
                "schema_version",
                "catalog_snapshot_sha256",
                "method",
                "nodes",
                "edges",
            ],
        },
        {
            "type": "command",
            "name": "authoritative-catalog-replay",
            "argv": [
                sys.executable,
                "-m",
                "learnfactory.catalog_synthesis",
                "validate",
                "--workspace",
                ".",
                "--database",
                str(db.path.resolve()),
                "--policy-sha256",
                policy_sha256,
            ],
            "env": {"PYTHONPATH": str(source_root)},
            "timeout_seconds": 120,
            "claims": ["TESTED"],
        },
        {"type": "tree_checksum", "name": "catalog-synthesis-tree-checksum"},
    ]
    return CatalogSynthesisResult(
        evidence={
            "handler": "generate_catalog_synthesis",
            "catalog_snapshot_sha256": documents.backlog["catalog_snapshot_sha256"],
            "source_count": documents.backlog["summary"]["sources"],
            "course_count": documents.backlog["summary"]["courses"],
            "project_count": documents.backlog["summary"]["projects"],
            "backlog_count": documents.backlog["summary"]["total_items"],
            "concept_count": documents.concept_map["summary"]["concepts"],
            "policy_sha256": policy_sha256,
            "external_validation_required": True,
            "candidate_tree_sha256": tree_sha256(workspace),
        },
        validators=validators,
        artifact_type="catalog-synthesis",
        semantic_path="synthesis/catalog-v1",
        metadata={
            "name": "Normalized catalog priority backlog and concept map",
            "type": "catalog-synthesis",
            "catalog_snapshot_sha256": documents.backlog["catalog_snapshot_sha256"],
            "policy_sha256": policy_sha256,
            "validation_target": "TESTED",
            "claim_scope": {
                "TESTED": "exact deterministic replay against authoritative normalized SQLite records",
                "not_claimed": [
                    "REVIEWED",
                    "BENCHMARKED",
                    "TRANSFER_VERIFIED",
                    "PRODUCTIONIZED",
                ],
            },
            "provenance": documents.provenance,
        },
    )


def validate_catalog_synthesis(
    workspace: Path,
    db: Database,
    *,
    expected_policy_sha256: str | None = None,
) -> list[str]:
    errors: list[str] = []
    try:
        backlog = json.loads((workspace / "BACKLOG.json").read_text(encoding="utf-8"))
        policy = backlog["policy"]
        if expected_policy_sha256 is not None:
            actual_policy_sha256 = _object_sha256(policy)
            if actual_policy_sha256 != expected_policy_sha256:
                return [
                    "BACKLOG.json: embedded policy differs from the job-authorized policy"
                ]
        expected = build_catalog_documents(
            db,
            weights=policy["weights"],
            manual_overrides=policy["manual_overrides"],
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError, CatalogSynthesisError) as error:
        return [f"cannot reconstruct catalog synthesis: {error}"]

    expected_files: dict[str, object] = {
        "BACKLOG.json": expected.backlog,
        "CONCEPT_MAP.json": expected.concept_map,
        "PROVENANCE.json": expected.provenance,
    }
    for name, value in expected_files.items():
        try:
            actual = json.loads((workspace / name).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{name}: {error}")
            continue
        # Python considers ``True == 1``.  Comparing canonical JSON retains
        # JSON scalar types, so a boolean cannot impersonate a numeric rank or
        # score during authoritative replay.
        if canonical_json(actual) != canonical_json(value):
            errors.append(f"{name}: differs from authoritative deterministic replay")
    expected_markdown = {
        "README.md": expected.readme,
        "BACKLOG.md": expected.backlog_markdown,
        "CONCEPT_MAP.md": expected.concept_markdown,
    }
    for name, content in expected_markdown.items():
        try:
            actual = (workspace / name).read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"{name}: {error}")
            continue
        if actual != content:
            errors.append(f"{name}: differs from authoritative deterministic replay")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic catalog synthesis validator")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--workspace", required=True, type=Path)
    validate.add_argument("--database", required=True, type=Path)
    validate.add_argument("--policy-sha256", required=True)
    args = parser.parse_args(argv)
    if args.command != "validate":
        parser.error("unknown command")
    errors = validate_catalog_synthesis(
        args.workspace.resolve(),
        Database(args.database.resolve(), Path(".")),
        expected_policy_sha256=args.policy_sha256,
    )
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("catalog synthesis exactly matches authoritative normalized state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
