from __future__ import annotations

import hashlib
import html
import re
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlsplit

from ..util import slugify
from .base import (
    BuildProjectRecord,
    GitSnapshot,
    NormalizedBatch,
    SourceAdapter,
    SourceDescriptor,
    git_snapshot,
)


_CATEGORY_RE = re.compile(r"^####\s+Build your own\s+`(?P<category>[^`]+)`\s*$")
_UNCATEGORIZED_RE = re.compile(r"^####\s+Uncategorized\s*$", re.IGNORECASE)
_ENTRY_RE = re.compile(
    r"^\*\s+\[\*\*(?P<language>.+?)\*\*:\s*(?P<title>.*?)\]"
    r"\((?P<url>.*?)\)(?P<suffix>.*)$"
)


_TIER_ONE = {
    "bittorrent client",
    "database",
    "distributed systems",
    "docker",
    "emulator / virtual machine",
    "git",
    "memory allocator",
    "network stack",
    "operating system",
    "programming language",
    "search engine",
    "shell",
    "web browser",
    "web server",
}
_TIER_TWO = {
    "3d renderer",
    "command-line tool",
    "front-end framework / library",
    "physics engine",
    "processor",
    "regex engine",
    "template engine",
    "text editor",
}
_CONCEPTS: dict[str, tuple[str, ...]] = {
    "bittorrent client": ("peer-to-peer", "networking", "protocols", "piece scheduling"),
    "command-line tool": ("command-line interfaces", "processes", "packaging"),
    "database": ("storage", "indexing", "persistence", "query processing"),
    "distributed systems": ("distributed systems", "replication", "consensus", "fault tolerance"),
    "docker": ("containers", "namespaces", "filesystems", "process isolation"),
    "emulator / virtual machine": ("instruction sets", "virtual machines", "interpreters"),
    "git": ("version control", "content addressing", "graphs", "filesystem storage"),
    "memory allocator": ("memory management", "fragmentation", "systems programming"),
    "network stack": ("networking", "protocols", "packet processing"),
    "operating system": ("operating systems", "processes", "virtual memory", "filesystems"),
    "processor": ("computer architecture", "instruction sets", "digital logic"),
    "programming language": ("parsing", "interpreters", "compilers", "language design"),
    "regex engine": ("automata", "parsing", "pattern matching"),
    "search engine": ("indexing", "information retrieval", "ranking"),
    "shell": ("processes", "pipes", "job control", "parsing"),
    "text editor": ("text data structures", "terminal interfaces", "incremental updates"),
    "web browser": ("networking", "parsing", "rendering", "security"),
    "web server": ("http", "sockets", "concurrency", "network services"),
}


@dataclass(frozen=True)
class _Tutorial:
    category: str
    language: str
    title: str
    url: str
    suffix: str
    line_number: int


def _clean_title(value: str) -> str:
    rendered = html.unescape(value.strip())
    rendered = rendered.replace("**", "").replace("__", "").replace("`", "")
    rendered = rendered.strip().strip("*_").strip()
    return re.sub(r"\s+", " ", rendered)


def _languages(value: str) -> tuple[str, ...]:
    return tuple(
        part.strip()
        for part in re.split(r"\s*(?:/|,)\s*", value)
        if part.strip()
    )


def _source_format(url: str, suffix: str) -> str:
    lowered_suffix = suffix.lower()
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.lower()
    if "[video]" in lowered_suffix or host in {
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "vimeo.com",
        "www.vimeo.com",
        "bilibili.com",
        "www.bilibili.com",
    }:
        return "video"
    if host in {
        "github.com",
        "www.github.com",
        "gitlab.com",
        "www.gitlab.com",
        "codeberg.org",
        "bitbucket.org",
    }:
        return "repository"
    if path.endswith(".pdf"):
        return "pdf"
    return "article"


def _priority(category: str) -> tuple[int, float, float]:
    normalized = category.lower()
    if normalized in _TIER_ONE:
        return 1, 8.0, 8.5
    if normalized in _TIER_TWO:
        return 2, 6.5, 6.5
    return 3, 5.0, 5.0


def _concepts(category: str) -> tuple[str, ...]:
    normalized = category.lower()
    specific = _CONCEPTS.get(normalized)
    if specific is not None:
        return specific
    generic = slugify(category).replace("-", " ")
    return (generic,) if generic else ()


class BuildYourOwnXAdapter(SourceAdapter):
    adapter_name = "build_your_own_x"
    source_type = "project_catalog"
    source_name = "Build Your Own X"
    extractor_version = "1.1"

    def detect_snapshot(self, snapshot: GitSnapshot) -> bool:
        readme = next(
            (entry for entry in snapshot.entries if entry.path == "README.md"), None
        )
        if readme is None or not readme.is_regular_blob:
            return False
        prefix = html.unescape(
            snapshot.read_blob("README.md").decode("utf-8", errors="replace")[:16_000]
        )
        return (
            "Build your own <insert-technology-here>" in prefix
            and "#### Build your own `" in prefix
        )

    def describe(self, path: Path) -> SourceDescriptor:
        descriptor = super().describe(path)
        raw = git_snapshot(descriptor.path, descriptor.commit_hash).read_blob("README.md")
        text = raw.decode("utf-8", errors="replace")
        if (
            "creativecommons.org/publicdomain/zero/1.0" in text
            and "waived all copyright and related or neighboring rights" in text
        ):
            return replace(
                descriptor,
                license="CC0-1.0",
                metadata={
                    **descriptor.metadata,
                    "license_file": "README.md#origins--license",
                    "license_sha256": hashlib.sha256(raw).hexdigest(),
                    "license_source_commit": descriptor.commit_hash,
                    "license_evidence": "explicit CC0 waiver declaration",
                    "linked_resource_license": "NOASSERTION",
                },
            )
        return descriptor

    def extract(self, descriptor: SourceDescriptor) -> NormalizedBatch:
        raw = git_snapshot(descriptor.path, descriptor.commit_hash).read_blob("README.md")
        text = raw.decode("utf-8", errors="replace")
        warnings: list[str] = []
        if "\ufffd" in text:
            warnings.append("README.md: invalid UTF-8 replaced")
        category: str | None = None
        tutorials: list[_Tutorial] = []
        for line_number, line in enumerate(text.splitlines(), 1):
            heading = _CATEGORY_RE.match(line.strip())
            if heading:
                category = html.unescape(heading.group("category").strip())
                continue
            if _UNCATEGORIZED_RE.match(line.strip()):
                category = "Uncategorized"
                continue
            if not line.startswith("* [**"):
                continue
            entry = _ENTRY_RE.match(line)
            if entry is None:
                warnings.append(f"README.md#L{line_number}: unparsed tutorial entry")
                continue
            if category is None:
                warnings.append(f"README.md#L{line_number}: tutorial has no category")
                continue
            url = entry.group("url").strip()
            if not re.match(r"^https?://", url, flags=re.IGNORECASE):
                warnings.append(f"README.md#L{line_number}: unsupported URL {url!r}")
                continue
            title = _clean_title(entry.group("title"))
            if not title:
                warnings.append(f"README.md#L{line_number}: tutorial has no title")
                continue
            tutorials.append(
                _Tutorial(
                    category=category,
                    language=_clean_title(entry.group("language")),
                    title=title,
                    url=url,
                    suffix=entry.group("suffix").strip(),
                    line_number=line_number,
                )
            )

        content_hash = hashlib.sha256(raw).hexdigest()
        base_slugs = [slugify(tutorial.title) for tutorial in tutorials]
        slug_counts = Counter(base_slugs)
        used_slugs: Counter[str] = Counter()
        projects: list[BuildProjectRecord] = []
        for tutorial, base_slug in zip(tutorials, base_slugs):
            slug = base_slug
            if slug_counts[base_slug] > 1:
                slug = f"{base_slug}-{slugify(tutorial.language)}"
            used_slugs[slug] += 1
            if used_slugs[slug] > 1:
                slug = f"{slug}-{hashlib.sha256(tutorial.url.encode('utf-8')).hexdigest()[:8]}"
            tier, difficulty, production_relevance = _priority(tutorial.category)
            languages = _languages(tutorial.language)
            projects.append(
                BuildProjectRecord(
                    key=tutorial.url,
                    slug=slug,
                    title=tutorial.title,
                    category=tutorial.category,
                    implementation_language=tutorial.language or None,
                    upstream_reference=tutorial.url,
                    concepts=_concepts(tutorial.category),
                    difficulty=difficulty,
                    production_relevance=production_relevance,
                    source_format=_source_format(tutorial.url, tutorial.suffix),
                    priority_tier=tier,
                    metadata={
                        "provenance": {
                            "classification": "source-derived",
                            "source_commit": descriptor.commit_hash,
                            "source_file": "README.md",
                            "source_line": tutorial.line_number,
                            "content_sha256": content_hash,
                            "adapter": self.adapter_name,
                            "extractor_version": self.extractor_version,
                        },
                        "languages": list(languages),
                        "catalog_suffix": tutorial.suffix,
                        "linked_resource_license": "NOASSERTION",
                        "scoring": {
                            "classification": "inferred",
                            "priority_tier": tier,
                            "basis": "category heuristic",
                        },
                    },
                )
            )
        return NormalizedBatch(projects=tuple(projects), warnings=tuple(warnings))


BuildYourOwnXSourceAdapter = BuildYourOwnXAdapter
