from __future__ import annotations

import contextlib
import hashlib
import os
import re
import shutil
import sqlite3
import subprocess
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import SplitResult, urlsplit, urlunsplit

from ..db import Database
from ..util import canonical_json, now


class SourceError(RuntimeError):
    """Base error for local source discovery and ingestion."""


class UnsupportedSourceError(SourceError):
    """Raised when no adapter recognizes a configured source path."""


class SourceFormatError(SourceError):
    """Raised when a recognized source is not safe or parseable."""


@dataclass(frozen=True)
class SourceDescriptor:
    source_id: str
    source_type: str
    name: str
    path: Path
    upstream_url: str | None
    commit_hash: str
    license: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CourseRecord:
    slug: str
    institution: str | None
    title: str
    topic: str | None
    description: str | None
    prerequisites: tuple[str, ...] = ()
    estimated_human_hours: float | None = None
    difficulty: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "DISCOVERED"


@dataclass(frozen=True)
class CourseUnitRecord:
    course_slug: str
    key: str
    unit_type: str
    order: int
    title: str
    dependencies: tuple[str, ...] = ()
    source_reference: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CurriculumEdgeRecord:
    from_course_slug: str
    to_course_slug: str
    relation: str
    evidence: str | None
    inferred: bool


@dataclass(frozen=True)
class BuildProjectRecord:
    key: str
    slug: str
    title: str
    category: str
    implementation_language: str | None
    upstream_reference: str
    concepts: tuple[str, ...] = ()
    difficulty: float | None = None
    production_relevance: float | None = None
    source_format: str | None = None
    priority_tier: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedBatch:
    courses: tuple[CourseRecord, ...] = ()
    units: tuple[CourseUnitRecord, ...] = ()
    curriculum_edges: tuple[CurriculumEdgeRecord, ...] = ()
    projects: tuple[BuildProjectRecord, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class IngestionResult:
    source_id: str
    source_name: str
    adapter: str
    courses: int
    course_units: int
    curriculum_edges: int
    projects: int
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "adapter": self.adapter,
            "courses": self.courses,
            "course_units": self.course_units,
            "curriculum_edges": self.curriculum_edges,
            "projects": self.projects,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class PreparedSourceIngestion:
    """An immutable, DB-free normalization result awaiting publication."""

    adapter: str
    descriptor: SourceDescriptor
    batch: NormalizedBatch
    prepared_at: float

    @property
    def source_metadata(self) -> dict[str, Any]:
        return {
            **self.descriptor.metadata,
            "last_ingestion": {
                "at": self.prepared_at,
                "courses": len(self.batch.courses),
                "course_units": len(self.batch.units),
                "curriculum_edges": len(self.batch.curriculum_edges),
                "projects": len(self.batch.projects),
                "warnings": list(self.batch.warnings),
            },
        }

    def result(self) -> IngestionResult:
        return IngestionResult(
            source_id=self.descriptor.source_id,
            source_name=self.descriptor.name,
            adapter=self.adapter,
            courses=len(self.batch.courses),
            course_units=len(self.batch.units),
            curriculum_edges=len(self.batch.curriculum_edges),
            projects=len(self.batch.projects),
            warnings=self.batch.warnings,
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the normalized snapshot persisted in the validated artifact."""

        return {
            "schema_version": 1,
            "adapter": self.adapter,
            "prepared_at": self.prepared_at,
            "descriptor": {
                "source_id": self.descriptor.source_id,
                "source_type": self.descriptor.source_type,
                "name": self.descriptor.name,
                "path": str(self.descriptor.path),
                "upstream_url": self.descriptor.upstream_url,
                "commit_hash": self.descriptor.commit_hash,
                "license": self.descriptor.license,
                "metadata": self.descriptor.metadata,
            },
            "normalized": {
                "courses": [asdict(item) for item in self.batch.courses],
                "course_units": [asdict(item) for item in self.batch.units],
                "curriculum_edges": [
                    asdict(item) for item in self.batch.curriculum_edges
                ],
                "projects": [asdict(item) for item in self.batch.projects],
                "warnings": list(self.batch.warnings),
            },
            "summary": self.result().as_dict(),
        }


def stable_id(prefix: str, *parts: str) -> str:
    material = "\0".join(parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(material).hexdigest()[:32]}"


def sanitize_remote_url(value: str | None) -> str | None:
    """Remove URL credentials while preserving ordinary Git SCP-style remotes."""
    if not value:
        return None
    candidate = value.strip()
    if "://" not in candidate:
        # git@host:path is an identity, not a credential-bearing URL.  Other
        # user@host forms are reduced to their host/path representation.
        if re.match(r"^[A-Za-z0-9_.-]+@[^:]+:", candidate):
            user, remainder = candidate.split("@", 1)
            return candidate if user == "git" else remainder
        return candidate
    parsed = urlsplit(candidate)
    hostname = parsed.hostname or ""
    try:
        port = parsed.port
    except ValueError:
        port = None
    if port is not None:
        hostname = f"{hostname}:{port}"
    # Queries and fragments are unnecessary for Git remotes and are plausible
    # places for providers to embed short-lived credentials.
    clean = SplitResult(parsed.scheme, hostname, parsed.path, "", "")
    return urlunsplit(clean)


def _git_environment() -> dict[str, str]:
    return {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_LITERAL_PATHSPECS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
    }


def _git_text(path: Path, *arguments: str, required: bool = True) -> str | None:
    executable = shutil.which("git")
    if executable is None:
        if required:
            raise SourceFormatError("git executable is unavailable")
        return None
    try:
        completed = subprocess.run(
            [executable, "-C", str(path), *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            check=False,
            env=_git_environment(),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        if required:
            raise SourceFormatError(f"cannot inspect Git repository {path}: {error}") from error
        return None
    if completed.returncode != 0:
        if required:
            detail = completed.stderr.strip() or f"git exited {completed.returncode}"
            raise SourceFormatError(f"cannot inspect Git repository {path}: {detail}")
        return None
    rendered = completed.stdout.strip()
    return rendered or None


def _git_bytes(path: Path, *arguments: str) -> bytes:
    executable = shutil.which("git")
    if executable is None:
        raise SourceFormatError("git executable is unavailable")
    try:
        completed = subprocess.run(
            [executable, "-C", str(path), *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
            env=_git_environment(),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SourceFormatError(f"cannot inspect Git repository {path}: {error}") from error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise SourceFormatError(
            f"cannot inspect Git repository {path}: "
            f"{detail or f'git exited {completed.returncode}'}"
        )
    return completed.stdout


_GIT_OBJECT_ID_RE = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})")
_REGULAR_GIT_MODES = frozenset({"100644", "100755"})
_MAX_SOURCE_BLOB_BYTES = 16 * 1024 * 1024
_MAX_TREE_ENTRIES = 100_000


def _validated_git_object_id(value: str, *, label: str) -> str:
    if not _GIT_OBJECT_ID_RE.fullmatch(value):
        raise SourceFormatError(f"unexpected Git {label}: {value!r}")
    return value.lower()


def _validated_git_path(value: str) -> str:
    if (
        not value
        or "\\" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise SourceFormatError(f"unsafe path in Git tree: {value!r}")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or any(part in {"", ".", ".."} for part in parsed.parts):
        raise SourceFormatError(f"unsafe path in Git tree: {value!r}")
    if parsed.as_posix() != value:
        raise SourceFormatError(f"non-canonical path in Git tree: {value!r}")
    return value


@dataclass(frozen=True)
class GitTreeEntry:
    """One immutable entry from a specific Git commit tree."""

    path: str
    mode: str
    object_type: str
    object_id: str
    size: int | None

    @property
    def is_regular_blob(self) -> bool:
        return self.object_type == "blob" and self.mode in _REGULAR_GIT_MODES

    @property
    def is_symlink(self) -> bool:
        return self.object_type == "blob" and self.mode == "120000"


@dataclass(frozen=True)
class GitSnapshot:
    """Read-only access to regular blobs reachable from one recorded commit."""

    repository: Path
    commit_hash: str
    tree_hash: str
    entries: tuple[GitTreeEntry, ...]

    def entries_under(self, prefix: str) -> tuple[GitTreeEntry, ...]:
        canonical = _validated_git_path(prefix)
        child_prefix = canonical + "/"
        return tuple(
            entry
            for entry in self.entries
            if entry.path == canonical or entry.path.startswith(child_prefix)
        )

    def read_blob(
        self, relative_path: str, *, max_bytes: int = _MAX_SOURCE_BLOB_BYTES
    ) -> bytes:
        canonical = _validated_git_path(relative_path)
        matches = [entry for entry in self.entries if entry.path == canonical]
        if not matches:
            raise SourceFormatError(
                f"tracked path is absent from commit {self.commit_hash}: {canonical}"
            )
        if len(matches) != 1:
            raise SourceFormatError(f"duplicate path in Git tree: {canonical}")
        entry = matches[0]
        if entry.is_symlink:
            raise SourceFormatError(f"refusing to read tracked symlink: {canonical}")
        if not entry.is_regular_blob:
            raise SourceFormatError(
                f"tracked path is not a regular blob: {canonical} "
                f"({entry.mode} {entry.object_type})"
            )
        if max_bytes < 0:
            raise ValueError("max_bytes must be nonnegative")
        if entry.size is None or entry.size > max_bytes:
            raise SourceFormatError(
                f"tracked blob exceeds {max_bytes} bytes: {canonical} ({entry.size})"
            )
        raw = _git_bytes(self.repository, "cat-file", "blob", entry.object_id)
        if len(raw) != entry.size:
            raise SourceFormatError(
                f"Git blob size changed while reading {canonical}: "
                f"expected {entry.size}, got {len(raw)}"
            )
        return raw


def git_head_commit(repository: Path) -> str:
    """Resolve HEAD to a commit without consulting tracked worktree files."""

    resolved = repository.expanduser().resolve(strict=True)
    if not resolved.is_dir():
        raise SourceFormatError(f"source path is not a directory: {resolved}")
    commit = _git_text(resolved, "rev-parse", "--verify", "HEAD^{commit}")
    assert commit is not None
    return _validated_git_object_id(commit, label="commit identifier")


def git_snapshot(repository: Path, commit_hash: str) -> GitSnapshot:
    """Load a commit tree without opening any path in the live worktree."""

    resolved = repository.expanduser().resolve(strict=True)
    if not resolved.is_dir():
        raise SourceFormatError(f"source path is not a directory: {resolved}")
    commit = _validated_git_object_id(commit_hash, label="commit identifier")
    tree = _git_text(resolved, "rev-parse", "--verify", f"{commit}^{{tree}}")
    assert tree is not None
    tree_hash = _validated_git_object_id(tree, label="tree identifier")
    raw_tree = _git_bytes(resolved, "ls-tree", "-rlz", "--full-tree", commit)
    records = raw_tree.split(b"\x00")
    if records and records[-1] == b"":
        records.pop()
    if len(records) > _MAX_TREE_ENTRIES:
        raise SourceFormatError(
            f"Git tree contains more than {_MAX_TREE_ENTRIES} entries"
        )
    entries: list[GitTreeEntry] = []
    paths: set[str] = set()
    for record in records:
        try:
            header, raw_path = record.split(b"\t", 1)
            mode_raw, type_raw, object_raw, size_raw = header.split()
            mode = mode_raw.decode("ascii")
            object_type = type_raw.decode("ascii")
            object_id = _validated_git_object_id(
                object_raw.decode("ascii"), label="object identifier"
            )
            relative_path = _validated_git_path(raw_path.decode("utf-8"))
            if size_raw != b"-" and not size_raw.isdigit():
                raise ValueError("invalid object size")
            size = None if size_raw == b"-" else int(size_raw)
        except (UnicodeDecodeError, ValueError) as error:
            raise SourceFormatError("malformed or non-UTF-8 entry in Git tree") from error
        if not re.fullmatch(r"[0-7]{6}", mode):
            raise SourceFormatError(f"invalid mode in Git tree: {mode!r}")
        if object_type not in {"blob", "commit"}:
            raise SourceFormatError(f"unexpected object type in Git tree: {object_type!r}")
        if size is not None and size < 0:
            raise SourceFormatError(f"negative size in Git tree: {relative_path}")
        if relative_path in paths:
            raise SourceFormatError(f"duplicate path in Git tree: {relative_path}")
        paths.add(relative_path)
        entries.append(
            GitTreeEntry(relative_path, mode, object_type, object_id, size)
        )
    return GitSnapshot(
        resolved,
        commit,
        tree_hash,
        tuple(sorted(entries, key=lambda entry: entry.path)),
    )


def git_tree_entries(repository: Path, commit_hash: str) -> tuple[GitTreeEntry, ...]:
    """Return immutable tracked entries for *commit_hash*."""

    return git_snapshot(repository, commit_hash).entries


def git_blob(repository: Path, commit_hash: str, relative_path: str) -> bytes:
    """Read one regular tracked blob and reject symlinks or non-tree paths."""

    return git_snapshot(repository, commit_hash).read_blob(relative_path)


def _license_metadata(snapshot: GitSnapshot) -> tuple[str, dict[str, Any]]:
    candidates = sorted(
        (
            entry
            for entry in snapshot.entries
            if "/" not in entry.path
            and entry.path.lower()
            in {
                "license",
                "license.md",
                "license.txt",
                "copying",
                "copying.md",
                "copying.txt",
            }
        ),
        key=lambda entry: entry.path,
    )
    if not candidates:
        return "NOASSERTION", {"license_file": None}
    selected = candidates[0]
    raw = snapshot.read_blob(selected.path, max_bytes=2 * 1024 * 1024)
    text = raw.decode("utf-8", errors="replace").lower()
    if "permission is hereby granted, free of charge" in text:
        identifier = "MIT"
    elif "apache license" in text and "version 2.0" in text:
        identifier = "Apache-2.0"
    elif "gnu general public license" in text and "version 3" in text:
        identifier = "GPL-3.0"
    elif "gnu general public license" in text and "version 2" in text:
        identifier = "GPL-2.0"
    elif "redistribution and use in source and binary forms" in text:
        identifier = "BSD"
    else:
        identifier = "NOASSERTION"
    return identifier, {
        "license_file": selected.path,
        "license_sha256": hashlib.sha256(raw).hexdigest(),
        "license_source_commit": snapshot.commit_hash,
    }


class SourceAdapter(ABC):
    """Read-only adapter that normalizes one local Git source repository."""

    adapter_name: str
    source_type: str
    source_name: str
    extractor_version = "1"

    @abstractmethod
    def detect_snapshot(self, snapshot: GitSnapshot) -> bool:
        """Return whether this adapter recognizes one immutable commit snapshot."""

    @abstractmethod
    def extract(self, descriptor: SourceDescriptor) -> NormalizedBatch:
        """Parse a previously described local source into normalized records."""

    def detect(self, path: Path) -> bool:
        """Recognize a repository by HEAD's tracked blobs, never live file contents."""

        try:
            resolved = path.expanduser().resolve(strict=True)
            snapshot = git_snapshot(resolved, git_head_commit(resolved))
            return self.detect_snapshot(snapshot)
        except (OSError, SourceError):
            return False

    def describe(self, path: Path) -> SourceDescriptor:
        resolved = path.expanduser().resolve(strict=True)
        if not resolved.is_dir():
            raise SourceFormatError(f"source path is not a directory: {resolved}")
        commit = git_head_commit(resolved)
        snapshot = git_snapshot(resolved, commit)
        if not self.detect_snapshot(snapshot):
            raise UnsupportedSourceError(
                f"{self.adapter_name} does not recognize {resolved} at {commit}"
            )
        remote = sanitize_remote_url(
            _git_text(resolved, "config", "--get", "remote.origin.url", required=False)
        )
        head_ref = _git_text(resolved, "symbolic-ref", "--short", "-q", "HEAD", required=False)
        status = _git_text(
            resolved, "status", "--porcelain", "--untracked-files=no", required=False
        )
        license_name, license_metadata = _license_metadata(snapshot)
        source_id = stable_id("source", self.source_type, str(resolved), commit)
        return SourceDescriptor(
            source_id=source_id,
            source_type=self.source_type,
            name=self.source_name,
            path=resolved,
            upstream_url=remote,
            commit_hash=commit,
            license=license_name,
            metadata={
                "adapter": self.adapter_name,
                "extractor_version": self.extractor_version,
                "head_ref": head_ref,
                "working_tree_dirty": bool(status),
                "snapshot_reader": "git-object-database",
                "tree_hash": snapshot.tree_hash,
                **license_metadata,
            },
        )

    def prepare(self, path: Path | str) -> PreparedSourceIngestion:
        """Normalize one pinned Git snapshot without changing authoritative state."""

        descriptor = self.describe(Path(path))
        batch = self.extract(descriptor)
        return PreparedSourceIngestion(self.adapter_name, descriptor, batch, now())

    def ingest(self, db: Database, path: Path | str) -> IngestionResult:
        # Parsing happens before the write transaction so NFS-backed SQLite
        # remains locked for as little time as possible.
        prepared = self.prepare(path)
        with db.transaction(immediate=True) as connection:
            return self.activate_prepared(db, connection, prepared)

    def activate_prepared(
        self,
        db: Database,
        connection: sqlite3.Connection,
        prepared: PreparedSourceIngestion,
    ) -> IngestionResult:
        """Publish a prepared snapshot in the caller's atomic transaction."""

        if prepared.adapter != self.adapter_name:
            raise SourceFormatError(
                f"prepared adapter {prepared.adapter!r} does not match {self.adapter_name!r}"
            )
        descriptor = prepared.descriptor
        batch = prepared.batch
        ingested_at = prepared.prepared_at
        source_metadata = prepared.source_metadata
        # The caller owns commit/rollback.  A borrowed context keeps the
        # reconciliation block visually scoped without nesting a transaction.
        with contextlib.nullcontext(connection) as connection:
            source_id = self._upsert_source(
                connection, descriptor, source_metadata, ingested_at
            )
            active_source = connection.execute(
                "SELECT source_id FROM sources WHERE path=? AND is_active=1",
                (str(descriptor.path),),
            ).fetchone()
            assert active_source is not None
            # Reconcile this exact immutable source snapshot with the current
            # extractor. Stable IDs are re-created below, while stale parser
            # output disappears instead of surviving forever after a fix.
            connection.execute(
                """
                DELETE FROM curriculum_edges
                WHERE from_course_id IN (SELECT course_id FROM courses WHERE source_id=?)
                   OR to_course_id IN (SELECT course_id FROM courses WHERE source_id=?)
                """,
                (source_id, source_id),
            )
            connection.execute(
                "DELETE FROM course_units WHERE course_id IN (SELECT course_id FROM courses WHERE source_id=?)",
                (source_id,),
            )
            connection.execute("DELETE FROM courses WHERE source_id=?", (source_id,))
            connection.execute("DELETE FROM build_projects WHERE source_id=?", (source_id,))
            course_ids: dict[str, str] = {}
            for course in batch.courses:
                course_id = stable_id("course", source_id, course.slug)
                connection.execute(
                    """
                    INSERT INTO courses(
                        course_id,source_id,slug,institution,title,topic,description,
                        prerequisites_json,estimated_human_hours,difficulty,
                        source_metadata_json,status
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(source_id,slug) DO UPDATE SET
                        institution=excluded.institution,
                        title=excluded.title,
                        topic=excluded.topic,
                        description=excluded.description,
                        prerequisites_json=excluded.prerequisites_json,
                        estimated_human_hours=excluded.estimated_human_hours,
                        difficulty=excluded.difficulty,
                        source_metadata_json=excluded.source_metadata_json
                    """,
                    (
                        course_id,
                        source_id,
                        course.slug,
                        course.institution,
                        course.title,
                        course.topic,
                        course.description,
                        canonical_json(list(course.prerequisites)),
                        course.estimated_human_hours,
                        course.difficulty,
                        canonical_json(course.metadata),
                        course.status,
                    ),
                )
                row = connection.execute(
                    "SELECT course_id FROM courses WHERE source_id=? AND slug=?",
                    (source_id, course.slug),
                ).fetchone()
                assert row is not None
                course_ids[course.slug] = row["course_id"]

            for unit in batch.units:
                course_id = course_ids.get(unit.course_slug)
                if course_id is None:
                    raise SourceFormatError(
                        f"unit {unit.key!r} refers to unknown course {unit.course_slug!r}"
                    )
                unit_id = stable_id("unit", course_id, unit.key)
                connection.execute(
                    """
                    INSERT INTO course_units(
                        unit_id,course_id,type,unit_order,title,dependencies_json,
                        source_reference,metadata_json
                    ) VALUES (?,?,?,?,?,?,?,?)
                    ON CONFLICT(unit_id) DO UPDATE SET
                        type=excluded.type,
                        unit_order=excluded.unit_order,
                        title=excluded.title,
                        dependencies_json=excluded.dependencies_json,
                        source_reference=excluded.source_reference,
                        metadata_json=excluded.metadata_json
                    """,
                    (
                        unit_id,
                        course_id,
                        unit.unit_type,
                        unit.order,
                        unit.title,
                        canonical_json(list(unit.dependencies)),
                        unit.source_reference,
                        canonical_json(unit.metadata),
                    ),
                )

            for edge in batch.curriculum_edges:
                from_id = course_ids.get(edge.from_course_slug)
                to_id = course_ids.get(edge.to_course_slug)
                if from_id is None or to_id is None or from_id == to_id:
                    continue
                connection.execute(
                    """
                    INSERT INTO curriculum_edges(
                        from_course_id,to_course_id,relation,evidence,inferred
                    ) VALUES (?,?,?,?,?)
                    ON CONFLICT(from_course_id,to_course_id,relation) DO UPDATE SET
                        evidence=excluded.evidence,
                        inferred=excluded.inferred
                    """,
                    (from_id, to_id, edge.relation, edge.evidence, int(edge.inferred)),
                )

            for project in batch.projects:
                project_id = stable_id("project", source_id, project.key)
                connection.execute(
                    """
                    INSERT INTO build_projects(
                        project_id,source_id,slug,title,category,implementation_language,
                        upstream_reference,concepts_json,difficulty,production_relevance,
                        source_format,priority_tier,metadata_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(source_id,upstream_reference) DO UPDATE SET
                        slug=excluded.slug,
                        title=excluded.title,
                        category=excluded.category,
                        implementation_language=excluded.implementation_language,
                        concepts_json=excluded.concepts_json,
                        difficulty=excluded.difficulty,
                        production_relevance=excluded.production_relevance,
                        source_format=excluded.source_format,
                        priority_tier=excluded.priority_tier,
                        metadata_json=excluded.metadata_json
                    """,
                    (
                        project_id,
                        source_id,
                        project.slug,
                        project.title,
                        project.category,
                        project.implementation_language,
                        project.upstream_reference,
                        canonical_json(list(project.concepts)),
                        project.difficulty,
                        project.production_relevance,
                        project.source_format,
                        project.priority_tier,
                        canonical_json(project.metadata),
                    ),
                )

            db.emit_event(
                "source-adapter",
                "SOURCE_INGESTED",
                payload={
                    "source_id": source_id,
                    "active_source_id": active_source["source_id"],
                    "activated": source_id == active_source["source_id"],
                    "adapter": self.adapter_name,
                    "commit_hash": descriptor.commit_hash,
                    "courses": len(batch.courses),
                    "course_units": len(batch.units),
                    "curriculum_edges": len(batch.curriculum_edges),
                    "projects": len(batch.projects),
                    "warnings": len(batch.warnings),
                },
                connection=connection,
            )
        return IngestionResult(
            source_id=source_id,
            source_name=descriptor.name,
            adapter=self.adapter_name,
            courses=len(batch.courses),
            course_units=len(batch.units),
            curriculum_edges=len(batch.curriculum_edges),
            projects=len(batch.projects),
            warnings=batch.warnings,
        )

    def _upsert_source(
        self,
        connection: sqlite3.Connection,
        descriptor: SourceDescriptor,
        metadata: dict[str, Any],
        ingested_at: float,
    ) -> str:
        existing = connection.execute(
            "SELECT source_id FROM sources WHERE path=? AND commit_hash=?",
            (str(descriptor.path), descriptor.commit_hash),
        ).fetchone()
        source_id = existing["source_id"] if existing is not None else descriptor.source_id
        if existing is None:
            connection.execute(
                """
                INSERT INTO sources(
                    source_id,type,name,path,upstream_url,commit_hash,license,
                    ingested_at,metadata_json,is_active
                ) VALUES (?,?,?,?,?,?,?,?,?,0)
                """,
                (
                    source_id,
                    descriptor.source_type,
                    descriptor.name,
                    str(descriptor.path),
                    descriptor.upstream_url,
                    descriptor.commit_hash,
                    descriptor.license,
                    ingested_at,
                    canonical_json(metadata),
                ),
            )
        else:
            connection.execute(
                """
                UPDATE sources SET
                    type=?,name=?,upstream_url=?,license=?,metadata_json=?
                WHERE source_id=?
                """,
                (
                    descriptor.source_type,
                    descriptor.name,
                    descriptor.upstream_url,
                    descriptor.license,
                    canonical_json(metadata),
                    source_id,
                ),
            )
        winner = connection.execute(
            """
            SELECT source_id,ingested_at FROM sources
            WHERE path=?
            ORDER BY ingested_at DESC,source_id DESC
            LIMIT 1
            """,
            (str(descriptor.path),),
        ).fetchone()
        assert winner is not None
        # Insertions begin inactive so the partial unique index remains valid.
        # The caller's BEGIN IMMEDIATE transaction makes this lifecycle switch
        # indivisible to readers and prevents concurrent double activation.
        connection.execute(
            """
            UPDATE sources
            SET is_active=0,superseded_by_source_id=?,superseded_at=?
            WHERE path=? AND source_id<>?
              AND (is_active=1 OR source_id=?)
            """,
            (
                winner["source_id"],
                winner["ingested_at"],
                str(descriptor.path),
                winner["source_id"],
                source_id,
            ),
        )
        connection.execute(
            """
            UPDATE sources
            SET is_active=1,superseded_by_source_id=NULL,superseded_at=NULL
            WHERE source_id=?
            """,
            (winner["source_id"],),
        )
        return source_id


def ingest_many(
    db: Database, adapter_paths: Iterable[tuple[SourceAdapter, Path | str]]
) -> tuple[IngestionResult, ...]:
    return tuple(adapter.ingest(db, path) for adapter, path in adapter_paths)
