from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from pathlib import PurePosixPath

from ..util import slugify
from .base import (
    CourseRecord,
    CourseUnitRecord,
    CurriculumEdgeRecord,
    GitSnapshot,
    NormalizedBatch,
    SourceAdapter,
    SourceDescriptor,
    SourceFormatError,
    git_snapshot,
)


_FIELD_RE = re.compile(
    # Brackets/parentheses are excluded so a Markdown link whose URL contains
    # ``https:`` cannot masquerade as a metadata key.
    r"^\s*[-*]\s+(?:\*\*)?(?P<key>[^:\n\[\]()<>]{2,80}?)(?:\*\*)?\s*:\s*(?P<value>.*)\s*$"
)
_HEADING_RE = re.compile(r"^(?P<level>#{1,6})\s+(?P<title>.+?)\s*$")
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(\s*(https?://[^\s)]+)\s*\)", re.IGNORECASE)
_ANGLE_URL_RE = re.compile(r"<(https?://[^>\s]+)>", re.IGNORECASE)
_BARE_URL_RE = re.compile(r"(?<![<(])(https?://[^\s<>)]+)", re.IGNORECASE)


def _normalized_key(value: str) -> str:
    value = value.replace("_", " ").replace("-", " ").strip().lower()
    return re.sub(r"\s+", " ", value)


def _plain_inline(value: str) -> str:
    value = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = value.replace("**", "").replace("__", "").replace("`", "")
    value = re.sub(r"<[^>]+>", "", value)
    return value.strip().strip("*_").strip()


def _urls(value: str) -> tuple[str, ...]:
    found: list[str] = []
    for pattern in (_MARKDOWN_LINK_RE, _ANGLE_URL_RE, _BARE_URL_RE):
        for match in pattern.finditer(value):
            url = match.group(1).rstrip(".,;")
            if url not in found:
                found.append(url)
    return tuple(found)


def _number(value: str) -> float | None:
    match = re.search(r"(?<![\d.])(\d+(?:\.\d+)?)", value)
    return float(match.group(1)) if match else None


def _difficulty(value: str) -> float | None:
    stars = value.count("🌟") + value.count("⭐")
    if stars:
        return float(stars)
    return _number(value)


def _prerequisites(value: str) -> tuple[str, ...]:
    rendered = _plain_inline(value)
    if not rendered or rendered.lower().rstrip(".") in {
        "none",
        "no",
        "n/a",
        "nil",
        "not required",
    }:
        return ()
    pieces = [piece.strip() for piece in re.split(r"\s*(?:,|;|\+)\s*", rendered)]
    return tuple(piece for piece in pieces if piece)


def _resource_type(key: str) -> str | None:
    normalized = _normalized_key(key)
    if any(token in normalized for token in ("exam", "midterm", "final")):
        return "exam"
    if "lab" in normalized:
        return "lab"
    if "project" in normalized and "assignment" not in normalized:
        return "project"
    if any(token in normalized for token in ("assignment", "homework", "exercise", "problem set")):
        return "assignment"
    if any(token in normalized for token in ("recording", "video", "lecture", "slide")):
        return "lecture"
    if any(
        token in normalized
        for token in (
            "course website",
            "course site",
            "text book",
            "textbook",
            "reading",
            "book",
            "paper",
            "note",
            "syllabus",
            "material",
        )
    ):
        return "reading"
    return None


def _availability(value: str, urls: tuple[str, ...]) -> str:
    lowered = value.lower()
    if any(
        marker in lowered
        for marker in (
            "not open source",
            "not open-source",
            "not available",
            "unavailable",
            "proprietary",
        )
    ):
        return "UNAVAILABLE"
    if urls:
        return "LINKED"
    if lowered.strip().rstrip(".") in {"none", "n/a", "nil"}:
        return "UNAVAILABLE"
    return "DESCRIBED"


def _description_bounds(lines: list[str]) -> tuple[int, int]:
    start = 0
    for index, line in enumerate(lines):
        match = _HEADING_RE.match(line.strip())
        if not match or len(match.group("level")) != 2:
            continue
        heading = _normalized_key(_plain_inline(match.group("title")))
        if heading in {"description", "descriptions", "course description"}:
            start = index + 1
            break
    end = len(lines)
    for index in range(start, len(lines)):
        match = _HEADING_RE.match(lines[index].strip())
        if match and len(match.group("level")) == 2:
            end = index
            break
    return start, end


def _title(lines: list[str], fallback: str) -> str:
    for line in lines:
        match = _HEADING_RE.match(line.strip())
        if match and len(match.group("level")) == 1:
            rendered = _plain_inline(match.group("title"))
            if rendered:
                return rendered
    return fallback


def _course_aliases(course: CourseRecord) -> set[str]:
    candidates = {course.slug, course.title.split(":", 1)[0]}
    source_stem = str(course.metadata.get("source_stem", ""))
    if source_stem:
        candidates.add(source_stem)
    candidates.update(
        re.findall(r"(?i)\b[A-Z]{1,8}\s*[-.]?\s*\d[\w.-]*\b", course.title)
    )
    aliases: set[str] = set()
    for candidate in candidates:
        canonical = re.sub(r"[^a-z0-9]", "", candidate.lower())
        if len(canonical) >= 4 and any(character.isdigit() for character in canonical):
            aliases.add(canonical)
    return aliases


class CSDIYAdapter(SourceAdapter):
    adapter_name = "csdiy"
    source_type = "course_catalog"
    source_name = "CSDIY"
    extractor_version = "1.1"

    def detect_snapshot(self, snapshot: GitSnapshot) -> bool:
        entries = {entry.path: entry for entry in snapshot.entries}
        return (
            entries.get("mkdocs.yml") is not None
            and entries["mkdocs.yml"].is_regular_blob
            and entries.get("template.en.md") is not None
            and entries["template.en.md"].is_regular_blob
            and any(entry.path.startswith("docs/") for entry in snapshot.entries)
        )

    def extract(self, descriptor: SourceDescriptor) -> NormalizedBatch:
        snapshot = git_snapshot(descriptor.path, descriptor.commit_hash)
        candidates: list[
            tuple[str, bytes, list[str], dict[str, tuple[str, int]]]
        ] = []
        warnings: list[str] = []
        source_entries = []
        for entry in snapshot.entries_under("docs"):
            if not entry.path.endswith(".en.md"):
                continue
            if entry.is_symlink:
                raise SourceFormatError(
                    f"CSDIY course entry is a tracked symlink: {entry.path}"
                )
            if not entry.is_regular_blob:
                raise SourceFormatError(
                    f"CSDIY course entry is not a regular blob: {entry.path}"
                )
            source_entries.append(entry)
        for entry in source_entries:
            relative = entry.path
            raw = snapshot.read_blob(relative)
            text = raw.decode("utf-8", errors="replace")
            if "\ufffd" in text:
                warnings.append(f"{relative}: invalid UTF-8 replaced")
            lines = text.splitlines()
            fields: dict[str, tuple[str, int]] = {}
            for line_number, line in enumerate(lines, 1):
                match = _FIELD_RE.match(line)
                if match:
                    fields.setdefault(
                        _normalized_key(match.group("key")),
                        (match.group("value").strip(), line_number),
                    )
            if "offered by" in fields:
                candidates.append((relative, raw, lines, fields))

        base_slugs = [
            slugify(PurePosixPath(path).name.removesuffix(".en.md"))
            for path, *_ in candidates
        ]
        slug_counts = Counter(base_slugs)
        courses: list[CourseRecord] = []
        units: list[CourseUnitRecord] = []
        for (path, raw, lines, fields), base_slug in zip(candidates, base_slugs):
            relative = path
            relative_docs = PurePosixPath(relative).relative_to("docs")
            topic = " / ".join(relative_docs.parts[:-1]) or "general"
            slug = (
                base_slug
                if slug_counts[base_slug] == 1
                else slugify(f"{topic}-{base_slug}")
            )
            source_name = PurePosixPath(relative).name
            course_title = _title(lines, source_name.removesuffix(".en.md"))
            start, end = _description_bounds(lines)
            description_lines: list[str] = []
            for line in lines[start:end]:
                field_match = _FIELD_RE.match(line)
                if field_match and _normalized_key(field_match.group("key")) in {
                    "offered by",
                    "prerequisite",
                    "prerequisites",
                    "programming language",
                    "programming languages",
                    "difficulty",
                    "class hour",
                    "class hours",
                    "instructor",
                }:
                    continue
                description_lines.append(line.rstrip())
            description = "\n".join(description_lines).strip() or None
            offered = fields["offered by"][0]
            prerequisite_value = fields.get(
                "prerequisites", fields.get("prerequisite", ("", 0))
            )[0]
            languages_value = fields.get(
                "programming languages", fields.get("programming language", ("", 0))
            )[0]
            difficulty_value = fields.get("difficulty", ("", 0))[0]
            hours_value = fields.get(
                "class hour", fields.get("class hours", ("", 0))
            )[0]
            content_hash = hashlib.sha256(raw).hexdigest()
            all_urls = _urls("\n".join(lines))
            raw_fields = {key: value for key, (value, _) in fields.items()}
            provenance = {
                "classification": "source-derived",
                "source_commit": descriptor.commit_hash,
                "source_file": relative,
                "content_sha256": content_hash,
                "adapter": self.adapter_name,
                "extractor_version": self.extractor_version,
            }
            course = CourseRecord(
                slug=slug,
                institution=_plain_inline(offered) or None,
                title=course_title,
                topic=topic,
                description=description,
                prerequisites=_prerequisites(prerequisite_value),
                estimated_human_hours=_number(hours_value),
                difficulty=_difficulty(difficulty_value),
                metadata={
                    "provenance": provenance,
                    "source_stem": source_name.removesuffix(".en.md"),
                    "programming_languages_raw": _plain_inline(languages_value),
                    "prerequisites_raw": _plain_inline(prerequisite_value),
                    "resource_urls": list(all_urls),
                    "fields": raw_fields,
                    "language": "en",
                },
            )
            courses.append(course)
            units.append(
                CourseUnitRecord(
                    course_slug=slug,
                    key=f"{relative}:catalog-overview",
                    unit_type="reading",
                    order=0,
                    title="Catalog overview and resource guide",
                    source_reference=relative,
                    metadata={
                        "provenance": provenance,
                        "role": "catalog_overview",
                        "official_course_unit": False,
                    },
                )
            )
            for line_number, line in enumerate(lines, 1):
                match = _FIELD_RE.match(line)
                if not match:
                    continue
                raw_key = _plain_inline(match.group("key"))
                unit_type = _resource_type(raw_key)
                if unit_type is None:
                    continue
                raw_value = match.group("value").strip()
                resource_urls = _urls(raw_value)
                units.append(
                    CourseUnitRecord(
                        course_slug=slug,
                        key=f"{relative}:line:{line_number}",
                        unit_type=unit_type,
                        order=line_number,
                        title=raw_key,
                        source_reference=f"{relative}#L{line_number}",
                        metadata={
                            "provenance": {
                                **provenance,
                                "source_line": line_number,
                            },
                            "raw_value": raw_value,
                            "urls": list(resource_urls),
                            "availability": _availability(raw_value, resource_urls),
                            "official_course_unit": unit_type
                            in {"lab", "assignment", "project", "exam"},
                        },
                    )
                )

            if not difficulty_value:
                warnings.append(f"{relative}: missing difficulty")
            if not hours_value:
                warnings.append(f"{relative}: missing class hour")

        edges = self._curriculum_edges(courses)
        return NormalizedBatch(
            courses=tuple(courses),
            units=tuple(units),
            curriculum_edges=tuple(edges),
            warnings=tuple(warnings),
        )

    def _curriculum_edges(
        self, courses: list[CourseRecord]
    ) -> list[CurriculumEdgeRecord]:
        aliases: dict[str, list[str]] = defaultdict(list)
        for course in courses:
            for alias in _course_aliases(course):
                aliases[alias].append(course.slug)
        unique_aliases = {
            alias: slugs[0] for alias, slugs in aliases.items() if len(set(slugs)) == 1
        }
        edges: dict[tuple[str, str], CurriculumEdgeRecord] = {}
        for course in courses:
            raw = str(course.metadata.get("prerequisites_raw", ""))
            canonical = re.sub(r"[^a-z0-9]", "", raw.lower())
            if not canonical:
                continue
            for alias, prerequisite_slug in sorted(
                unique_aliases.items(), key=lambda item: len(item[0]), reverse=True
            ):
                if prerequisite_slug == course.slug or alias not in canonical:
                    continue
                key = (prerequisite_slug, course.slug)
                edges[key] = CurriculumEdgeRecord(
                    from_course_slug=prerequisite_slug,
                    to_course_slug=course.slug,
                    relation="prerequisite",
                    evidence=f"Prerequisites: {raw}",
                    # The prerequisite text is explicit, but resolving its name
                    # to another catalog record is an adapter inference.
                    inferred=True,
                )
        return list(edges.values())


CSDIYSourceAdapter = CSDIYAdapter
