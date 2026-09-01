"""Read-only adapters for the factory's configured public source catalogs."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..db import Database
from .base import (
    BuildProjectRecord,
    CourseRecord,
    CourseUnitRecord,
    CurriculumEdgeRecord,
    GitSnapshot,
    GitTreeEntry,
    IngestionResult,
    NormalizedBatch,
    PreparedSourceIngestion,
    SourceAdapter,
    SourceDescriptor,
    SourceError,
    SourceFormatError,
    UnsupportedSourceError,
    git_blob,
    git_head_commit,
    git_snapshot,
    git_tree_entries,
)
from .build_your_own_x import BuildYourOwnXAdapter, BuildYourOwnXSourceAdapter
from .csdiy import CSDIYAdapter, CSDIYSourceAdapter


_ADAPTERS: tuple[SourceAdapter, ...] = (CSDIYAdapter(), BuildYourOwnXAdapter())


def available_adapters() -> tuple[SourceAdapter, ...]:
    return _ADAPTERS


def detect(path: Path | str) -> SourceAdapter | None:
    candidate = Path(path).expanduser()
    for adapter in _ADAPTERS:
        if adapter.detect(candidate):
            return adapter
    return None


def describe(path: Path | str) -> SourceDescriptor:
    adapter = detect(path)
    if adapter is None:
        raise UnsupportedSourceError(f"no source adapter recognizes {Path(path)}")
    return adapter.describe(Path(path))


def ingest(db: Database, path: Path | str) -> IngestionResult:
    adapter = detect(path)
    if adapter is None:
        raise UnsupportedSourceError(f"no source adapter recognizes {Path(path)}")
    return adapter.ingest(db, path)


def ingest_many(db: Database, paths: Iterable[Path | str]) -> tuple[IngestionResult, ...]:
    return tuple(ingest(db, path) for path in paths)


# Explicit names are convenient at CLI call sites and make the short API
# unambiguous when imported alongside job ingestion functions.
detect_source = detect
ingest_source = ingest


__all__ = [
    "BuildProjectRecord",
    "BuildYourOwnXAdapter",
    "BuildYourOwnXSourceAdapter",
    "CSDIYAdapter",
    "CSDIYSourceAdapter",
    "CourseRecord",
    "CourseUnitRecord",
    "CurriculumEdgeRecord",
    "GitSnapshot",
    "GitTreeEntry",
    "IngestionResult",
    "NormalizedBatch",
    "PreparedSourceIngestion",
    "SourceAdapter",
    "SourceDescriptor",
    "SourceError",
    "SourceFormatError",
    "UnsupportedSourceError",
    "available_adapters",
    "describe",
    "detect",
    "detect_source",
    "ingest",
    "ingest_many",
    "ingest_source",
    "git_blob",
    "git_head_commit",
    "git_snapshot",
    "git_tree_entries",
]
