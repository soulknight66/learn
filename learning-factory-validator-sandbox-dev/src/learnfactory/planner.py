from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .db import Database
from .util import json_value


@dataclass(frozen=True)
class PlanItem:
    order: int
    kind: str
    identifier: str
    title: str
    topic: str
    hours: float
    rationale: str
    source_reference: str | None


def curriculum_plan(
    db: Database,
    *,
    topic: str,
    weeks: int = 12,
    hours_per_week: float = 10,
    language: str | None = None,
    persona: str = "target",
) -> dict[str, Any]:
    budget = weeks * hours_per_week
    needle = topic.casefold()
    language_needle = language.casefold() if language else None
    with db.transaction() as connection:
        courses = [dict(row) for row in connection.execute(
            """
            SELECT c.course_id,c.title,c.topic,c.description,c.estimated_human_hours,
                   c.difficulty,c.source_metadata_json
            FROM courses AS c JOIN sources AS s ON s.source_id=c.source_id
            WHERE s.is_active=1
              AND (lower(c.topic) LIKE ? OR lower(c.title) LIKE ? OR lower(c.description) LIKE ?)
            ORDER BY c.difficulty DESC,c.estimated_human_hours ASC,c.title
            """,
            (f"%{needle}%", f"%{needle}%", f"%{needle}%"),
        )]
        projects = [dict(row) for row in connection.execute(
            """
            SELECT p.project_id,p.title,p.category,p.implementation_language,
                   p.upstream_reference,p.concepts_json,p.difficulty,
                   p.production_relevance,p.priority_tier
            FROM build_projects AS p JOIN sources AS s ON s.source_id=p.source_id
            WHERE s.is_active=1
              AND (lower(p.category) LIKE ? OR lower(p.concepts_json) LIKE ? OR lower(p.title) LIKE ?)
            ORDER BY p.priority_tier,p.production_relevance DESC,p.difficulty DESC,p.title
            """,
            (f"%{needle}%", f"%{needle}%", f"%{needle}%"),
        )]
        if not courses and not projects:
            # Broad system-oriented fallback still gives a useful plan for terms
            # such as "C++ systems programming" that are split across fields.
            courses = [dict(row) for row in connection.execute(
                """
                SELECT c.course_id,c.title,c.topic,c.description,c.estimated_human_hours,
                       c.difficulty,c.source_metadata_json
                FROM courses AS c JOIN sources AS s ON s.source_id=c.source_id
                WHERE s.is_active=1
                  AND c.topic IN ('操作系统','数据库系统','计算机网络','软件工程','体系结构')
                ORDER BY c.difficulty DESC,c.title LIMIT 20
                """
            )]
            projects = [dict(row) for row in connection.execute(
                """
                SELECT p.project_id,p.title,p.category,p.implementation_language,
                       p.upstream_reference,p.concepts_json,p.difficulty,
                       p.production_relevance,p.priority_tier
                FROM build_projects AS p JOIN sources AS s ON s.source_id=p.source_id
                WHERE s.is_active=1 AND p.priority_tier=1
                ORDER BY p.production_relevance DESC,p.difficulty DESC,p.title LIMIT 40
                """
            )]

    if language_needle:
        matching = [
            project for project in projects
            if language_needle in (project["implementation_language"] or "").casefold()
        ]
        if matching:
            projects = matching

    items: list[PlanItem] = []
    remaining = budget
    # Courses are intentionally sampled rather than consumed whole: the archive
    # contains units and projects, while linked material availability varies.
    for course in courses[:3]:
        full_hours = float(course["estimated_human_hours"] or 40)
        hours = min(full_hours, max(12.0, budget * 0.28))
        if hours > remaining and items:
            continue
        metadata = json_value(course["source_metadata_json"], {})
        provenance = metadata.get("provenance", {})
        items.append(
            PlanItem(
                len(items) + 1,
                "course",
                course["course_id"],
                course["title"],
                course["topic"] or "general",
                hours,
                "Build conceptual depth and use course labs as the canonical baseline.",
                provenance.get("source_file"),
            )
        )
        remaining -= hours
        if remaining <= 0:
            break

    for project in projects:
        if remaining < 4:
            break
        hours = min(18.0 if project["priority_tier"] == 1 else 10.0, remaining)
        items.append(
            PlanItem(
                len(items) + 1,
                "build-project",
                project["project_id"],
                project["title"],
                project["category"],
                hours,
                "Convert theory into a tested implementation, then review production gaps.",
                project["upstream_reference"],
            )
        )
        remaining -= hours

    rendered = [item.__dict__ for item in items]
    return {
        "persona": persona,
        "query": {"topic": topic, "language": language},
        "weeks": weeks,
        "hours_per_week": hours_per_week,
        "budget_hours": budget,
        "planned_hours": sum(item.hours for item in items),
        "items": rendered,
        "policy": (
            "For the target persona, pair each canonical task with debugging, production review, "
            "and an unseen transfer task; reveal sealed material only after an independent attempt."
        ),
    }


def plan_markdown(plan: dict[str, Any]) -> str:
    lines = [
        f"# {plan['weeks']}-week learning plan: {plan['query']['topic']}",
        "",
        f"Persona: `{plan['persona']}`. Budget: {plan['budget_hours']:.1f} hours; planned: {plan['planned_hours']:.1f} hours.",
        "",
    ]
    for item in plan["items"]:
        lines.extend(
            [
                f"## {item['order']}. {item['title']}",
                "",
                f"- Type: {item['kind']}",
                f"- Topic: {item['topic']}",
                f"- Time box: {item['hours']:.1f} hours",
                f"- Why: {item['rationale']}",
                f"- Source: {item['source_reference'] or 'catalog metadata'}",
                "",
            ]
        )
    lines.extend(["## Execution policy", "", plan["policy"], ""])
    return "\n".join(lines)
