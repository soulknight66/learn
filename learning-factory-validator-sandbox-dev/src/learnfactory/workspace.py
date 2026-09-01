from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .db import Database
from .util import canonical_json, file_sha256, json_value, new_id, now, tree_sha256


class WorkspaceError(RuntimeError):
    pass


_JOB_ID_RE = re.compile(r"^job_[A-Za-z0-9][A-Za-z0-9_.-]{0,155}$")
_ATTEMPT_DIRECTORY_RE = re.compile(r"^attempt-[0-9]+$")


def safe_relative(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise WorkspaceError(f"unsafe relative path: {value!r}")
    return path


def contained(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class PreparedArtifact:
    artifact_id: str
    path: Path
    checksum: str
    checksum_algorithm: str
    attempt: int
    artifact_type: str
    metadata: dict[str, Any]
    validation_status: str
    validation_labels: tuple[str, ...]
    created_at: float


class WorkspaceManager:
    PUBLIC_EXERCISE_NAMES = {
        "README.md",
        "MANIFEST.yaml",
        "REQUIREMENTS.md",
        "CONCEPTS.md",
        "DESIGN_QUESTIONS.md",
        "AGENTS.md",
        "starter",
        "public_tests",
        "environment",
    }

    def __init__(self, warehouse: Path, db: Database):
        self.warehouse = warehouse
        self.db = db
        self.workspaces = warehouse / "workspaces"
        self.artifacts = warehouse / "artifacts"

    def initialize(self) -> None:
        for path in (
            self.warehouse,
            self.workspaces,
            self.artifacts,
            self.warehouse / "logs",
            self.warehouse / "sources",
            self.warehouse / "courses",
            self.warehouse / "projects",
            self.warehouse / "learners",
            self.warehouse / "evaluations",
            self.warehouse / "catalog",
            self.warehouse / "challenges",
            self.warehouse / "benchmarks",
            self.warehouse / "synthesis",
        ):
            path.mkdir(parents=True, exist_ok=True)

    def allocate(self, job_id: str, attempt: int) -> Path:
        if _JOB_ID_RE.fullmatch(job_id) is None:
            raise WorkspaceError(f"unexpected job id: {job_id}")
        if attempt < 1:
            raise WorkspaceError(f"attempt must be positive: {attempt}")
        path = self.workspaces / job_id / f"attempt-{attempt:03d}"
        if not contained(self.workspaces, path):
            raise WorkspaceError("workspace path escapes managed workspace store")
        path.mkdir(parents=True, exist_ok=False)
        (path / ".factory-workspace").write_text(
            f"job_id={job_id}\nattempt={attempt}\n", encoding="utf-8"
        )
        return path

    def discard_root_metadata(self, workspace: Path, name: str) -> bool:
        """Remove one orchestrator-owned root metadata entry before validation.

        Codex may initialize its allocated directory as a Git repository while it
        works.  Repository metadata is neither learner output nor reproducibility
        evidence, and must not be promoted with an artifact.  The method accepts
        a single root name (not an arbitrary path) and is fenced to an allocated
        workspace so callers cannot turn it into a general deletion primitive.
        """

        if (
            workspace.is_symlink()
            or not workspace.is_dir()
            or not contained(self.workspaces, workspace)
        ):
            raise WorkspaceError("metadata cleanup requires an allocated workspace")
        relative = safe_relative(name)
        if len(relative.parts) != 1:
            raise WorkspaceError(f"unsafe root metadata name: {name!r}")
        target = workspace / relative
        if not target.exists() and not target.is_symlink():
            return False
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
        else:
            raise WorkspaceError(f"root metadata is a special file: {name!r}")
        return True

    def stage_file(self, source: Path, workspace: Path, destination: str) -> Path:
        if source.is_symlink() or not source.is_file():
            raise WorkspaceError(f"staged input must be a regular file: {source}")
        target = workspace / safe_relative(destination)
        if not contained(workspace, target):
            raise WorkspaceError(f"staged destination escapes workspace: {destination}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        target.chmod(target.stat().st_mode & ~0o222)
        return target

    def stage_tree(self, source: Path, workspace: Path, destination: str) -> Path:
        """Stage a regular, symlink-free directory as a read-only input tree."""

        if source.is_symlink() or not source.is_dir():
            raise WorkspaceError(f"staged input must be a directory: {source}")
        entries = list(source.rglob("*"))
        if any(path.is_symlink() for path in entries):
            raise WorkspaceError(f"staged input tree contains a symlink: {source}")
        if any(not path.is_file() and not path.is_dir() for path in entries):
            raise WorkspaceError(f"staged input tree contains a special file: {source}")
        target = workspace / safe_relative(destination)
        if not contained(workspace, target):
            raise WorkspaceError(f"staged destination escapes workspace: {destination}")
        if target.exists() or target.is_symlink():
            raise WorkspaceError(f"staged destination already exists: {destination}")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copytree(source, target, symlinks=True)
            copied = list(target.rglob("*"))
            if any(path.is_symlink() for path in copied):
                raise WorkspaceError(f"staged copy contains a symlink: {destination}")
            if any(not path.is_file() and not path.is_dir() for path in copied):
                raise WorkspaceError(f"staged copy contains a special file: {destination}")
            for path in copied:
                if path.is_file():
                    path.chmod(path.stat().st_mode & ~0o222)
            for path in sorted(
                (item for item in copied if item.is_dir()),
                key=lambda item: len(item.parts),
                reverse=True,
            ):
                path.chmod(path.stat().st_mode & ~0o222)
            target.chmod(target.stat().st_mode & ~0o222)
        except BaseException:
            if target.exists() or target.is_symlink():
                shutil.rmtree(target)
            raise
        return target

    def create_archive_projection(
        self, workspace: Path, selected_paths: tuple[str, ...]
    ) -> Path:
        """Copy only declared worker outputs into a transient archive candidate.

        Validators still inspect the complete workspace, including immutable staged
        inputs.  Archiving reviewers and examiners should not duplicate those inputs
        (especially sealed references and rubrics), so publication uses this
        symlink-free projection while provenance retains their checksums.
        """

        if (
            workspace.is_symlink()
            or not workspace.is_dir()
            or not contained(self.workspaces, workspace)
        ):
            raise WorkspaceError("archive projection requires an allocated workspace")
        if not selected_paths:
            raise WorkspaceError("archive projection requires at least one output path")
        relative_paths: list[Path] = []
        for raw in selected_paths:
            if not isinstance(raw, str):
                raise WorkspaceError("archive projection paths must be text")
            relative = safe_relative(raw)
            if any(
                relative == existing
                or relative in existing.parents
                or existing in relative.parents
                for existing in relative_paths
            ):
                raise WorkspaceError(
                    f"archive projection paths overlap: {relative.as_posix()}"
                )
            relative_paths.append(relative)

        projection = Path(
            # Keep crash leftovers attributed to the exact job attempt instead
            # of creating anonymous siblings in the global workspace store.
            tempfile.mkdtemp(prefix=".archive-projection-", dir=workspace)
        )
        try:
            for relative in sorted(relative_paths, key=lambda item: item.as_posix()):
                source = workspace / relative
                if not contained(workspace, source):
                    raise WorkspaceError(
                        f"archive projection source escapes workspace: {relative.as_posix()}"
                    )
                cursor = workspace
                for part in relative.parts:
                    cursor /= part
                    if cursor.is_symlink():
                        raise WorkspaceError(
                            "archive projection output contains a symlinked path "
                            f"component: {relative.as_posix()}"
                        )
                before = _projection_entry_fingerprint(
                    source, relative.as_posix()
                )
                destination = projection / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                if before[0] == "file":
                    # Do not follow a source that is replaced with a symlink
                    # between the checks above and the copy.  A copied symlink is
                    # rejected by the post-copy inspection below instead of
                    # silently importing bytes from outside the workspace.
                    shutil.copy2(source, destination, follow_symlinks=False)
                elif before[0] == "directory":
                    shutil.copytree(source, destination, symlinks=True)
                else:
                    raise WorkspaceError(
                        f"archive projection output is not regular: {relative.as_posix()}"
                    )
                after = _projection_entry_fingerprint(
                    source, relative.as_posix()
                )
                copied = _projection_entry_fingerprint(
                    destination, relative.as_posix()
                )
                if before != after or before != copied:
                    raise WorkspaceError(
                        "archive projection output changed while it was copied: "
                        f"{relative.as_posix()}"
                    )
            return projection
        except BaseException as error:
            if projection.exists():
                try:
                    _discard_owned_tree(projection)
                except OSError as cleanup_error:
                    error.add_note(
                        f"archive projection cleanup also failed: {cleanup_error}"
                    )
            raise

    def discard_archive_projection(self, projection: Path) -> None:
        """Remove only a projection created inside an allocated attempt."""

        try:
            parent_relative = projection.parent.resolve().relative_to(
                self.workspaces.resolve()
            )
        except ValueError as error:
            raise WorkspaceError("refusing to discard a non-projection path") from error

        if (
            projection.is_symlink()
            or len(parent_relative.parts) != 2
            or _JOB_ID_RE.fullmatch(parent_relative.parts[0]) is None
            or _ATTEMPT_DIRECTORY_RE.fullmatch(parent_relative.parts[1]) is None
            or not projection.name.startswith(".archive-projection-")
        ):
            raise WorkspaceError("refusing to discard a non-projection path")
        if projection.exists():
            _discard_owned_tree(projection)

    def create_student_view(self, challenge: Path, destination: Path) -> Path:
        """Copy only learner-visible entries and reject every symlink."""
        if not challenge.is_dir():
            raise WorkspaceError(f"challenge does not exist: {challenge}")
        if destination.exists():
            raise WorkspaceError(f"student view already exists: {destination}")
        destination.mkdir(parents=True)
        for child in challenge.iterdir():
            if child.name not in self.PUBLIC_EXERCISE_NAMES:
                continue
            descendants = list(child.rglob("*")) if child.is_dir() else []
            for candidate in [child, *descendants]:
                if candidate.is_symlink():
                    raise WorkspaceError(f"student-visible input contains symlink: {candidate}")
            target = destination / child.name
            if child.is_dir():
                shutil.copytree(child, target)
            else:
                shutil.copy2(child, target)
        if (destination / "sealed").exists():
            raise WorkspaceError("sealed material leaked into student view")
        (destination / ".isolated-view").write_text("label=ISOLATED_VIEW\n", encoding="utf-8")
        return destination

    def prepare_archive(
        self,
        job_id: str,
        attempt: int,
        candidate: Path,
        *,
        artifact_type: str,
        semantic_path: str,
        metadata: dict[str, Any],
        validation_status: str = "TESTED",
        validation_labels: list[str] | None = None,
    ) -> PreparedArtifact:
        """Copy a validated candidate but do not publish it in authoritative state.

        The job repository publishes this prepared tree and transitions the job in
        one transaction. A crash between preparation and publication can leave an
        unreferenced directory, never a falsely promoted catalog artifact.
        """
        if not candidate.is_dir() or not contained(self.workspaces, candidate):
            raise WorkspaceError("only an allocated workspace directory can be archived")
        if candidate.is_symlink() or any(path.is_symlink() for path in candidate.rglob("*")):
            raise WorkspaceError("artifact candidates may not contain symlinks")
        semantic = safe_relative(semantic_path)
        destination = self.artifacts / semantic / job_id / f"attempt-{attempt:03d}"
        if not contained(self.artifacts, destination):
            raise WorkspaceError("artifact destination escapes the artifact store")
        if destination.exists():
            raise WorkspaceError(f"artifact destination already exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        _fsync_directory_chain(destination.parent, self.warehouse)
        staging = Path(
            tempfile.mkdtemp(
                prefix=f".{job_id}-attempt-{attempt:03d}-",
                suffix=".staging",
                dir=destination.parent,
            )
        )
        renamed = False
        try:
            shutil.copytree(candidate, staging, symlinks=True, dirs_exist_ok=True)
            _fsync_tree(staging)
            checksum = tree_sha256(staging)
            if destination.exists():
                raise WorkspaceError(
                    f"artifact destination already exists: {destination}"
                )
            os.rename(staging, destination)
            renamed = True
            _fsync_directory(destination)
            _fsync_directory_chain(destination.parent, self.warehouse)
        except BaseException:
            cleanup = destination if renamed else staging
            if cleanup.exists():
                shutil.rmtree(cleanup)
                try:
                    _fsync_directory_chain(destination.parent, self.warehouse)
                except OSError:
                    pass
            raise
        identifier = new_id("artifact")
        labels = tuple(validation_labels or ["GENERATED"])
        return PreparedArtifact(
            identifier,
            destination,
            checksum,
            "tree-sha256-v2",
            attempt,
            artifact_type,
            dict(metadata),
            validation_status,
            labels,
            now(),
        )

    def discard_prepared(self, artifact: PreparedArtifact) -> None:
        """Remove an unpublished tree after a fenced publication failure."""

        if not contained(self.artifacts, artifact.path):
            raise WorkspaceError("refusing to discard outside the artifact store")
        if artifact.path.exists():
            shutil.rmtree(artifact.path)
            _fsync_directory_chain(artifact.path.parent, self.warehouse)

    def reconcile_published_artifacts(self) -> int:
        """Quarantine v2 records whose durable tree is absent or no longer matches.

        SQLite remains authoritative, but a database commit and a filesystem rename
        cannot be one transaction.  Startup verification fails closed after a host or
        storage crash instead of continuing to advertise or stage damaged bytes.
        """

        with self.db.connect() as connection:
            rows = list(
                connection.execute(
                    """
                    SELECT artifact_id,job_id,path,checksum
                    FROM artifacts
                    WHERE checksum_algorithm='tree-sha256-v2'
                      AND integrity_status='VERIFIED_V2'
                    ORDER BY artifact_id
                    """
                )
            )
        quarantined = 0
        for row in rows:
            path = Path(row["path"])
            reason: str | None = None
            if not contained(self.artifacts, path):
                reason = "published artifact path is outside the artifact store"
            elif path.is_symlink() or not path.is_dir():
                reason = "published artifact tree is missing or is not a real directory"
            else:
                try:
                    entries = list(path.rglob("*"))
                    if any(item.is_symlink() for item in entries):
                        reason = "published artifact tree contains a symbolic link"
                    elif any(
                        not item.is_file() and not item.is_dir() for item in entries
                    ):
                        reason = "published artifact tree contains a special file"
                    elif tree_sha256(path) != row["checksum"]:
                        reason = "published artifact tree checksum no longer matches"
                except OSError as error:
                    reason = f"published artifact tree cannot be verified: {error}"
            if reason is None:
                continue
            with self.db.transaction(immediate=True) as connection:
                changed = connection.execute(
                    """
                    UPDATE artifacts
                    SET integrity_status='LEGACY_UNVERIFIED',
                        validation_status=CASE
                          WHEN '+' || validation_status || '+' LIKE '%+PARTIAL+%'
                          THEN validation_status
                          ELSE validation_status || '+PARTIAL'
                        END
                    WHERE artifact_id=? AND integrity_status='VERIFIED_V2'
                    """,
                    (row["artifact_id"],),
                )
                if changed.rowcount != 1:
                    continue
                existing = connection.execute(
                    """
                    SELECT evidence_json FROM artifact_validation_labels
                    WHERE artifact_id=? AND label='PARTIAL'
                    """,
                    (row["artifact_id"],),
                ).fetchone()
                evidence: dict[str, Any] = {
                    "integrity_quarantine": True,
                    "reason": reason,
                    "checked_at": now(),
                }
                if existing is not None:
                    evidence["previous_evidence"] = json_value(
                        existing["evidence_json"], {}
                    )
                connection.execute(
                    """
                    INSERT INTO artifact_validation_labels(
                        artifact_id,label,evidence_json,created_at
                    ) VALUES (?,'PARTIAL',?,?)
                    ON CONFLICT(artifact_id,label) DO UPDATE SET
                        evidence_json=excluded.evidence_json,
                        created_at=excluded.created_at
                    """,
                    (
                        row["artifact_id"],
                        canonical_json(evidence),
                        evidence["checked_at"],
                    ),
                )
                self.db.emit_event(
                    "archivist",
                    "ARTIFACT_INTEGRITY_QUARANTINED",
                    job_id=row["job_id"],
                    payload={
                        "artifact_id": row["artifact_id"],
                        "path": str(path),
                        "reason": reason,
                    },
                    connection=connection,
                )
                quarantined += 1
        return quarantined

    def bwrap_command(self, argv: list[str], workspace: Path, *, network: bool = False) -> list[str]:
        """Build a minimal bubblewrap argv exposing no factory warehouse other than this workspace."""
        if not contained(self.workspaces, workspace) and not contained(self.warehouse / "learners", workspace):
            raise WorkspaceError("bubblewrap workspace must be factory-managed")
        command = [
            "bwrap",
            "--die-with-parent",
            "--new-session",
            "--unshare-user",
            "--unshare-pid",
            "--unshare-uts",
            "--unshare-ipc",
        ]
        if not network:
            command.append("--unshare-net")
        command.extend(
            [
                "--proc", "/proc",
                "--dev", "/dev",
                "--tmpfs", "/tmp",
                "--ro-bind", "/usr", "/usr",
                "--symlink", "usr/bin", "/bin",
                "--symlink", "usr/lib", "/lib",
                "--symlink", "usr/lib64", "/lib64",
                "--ro-bind", "/arm", "/arm",
                "--ro-bind", "/etc", "/etc",
                "--bind", str(workspace), "/workspace",
                "--chdir", "/workspace",
                "--setenv", "HOME", "/tmp",
                "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
                "--",
                *argv,
            ]
        )
        return command


def _open_for_fsync(path: Path, *, directory: bool = False) -> int:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if directory:
        flags |= getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    return os.open(path, flags)


def _discard_owned_tree(path: Path) -> None:
    """Remove a factory-owned scratch tree even when outputs are read-only.

    Projection copies intentionally preserve executable and permission bits for
    the eventual artifact.  A worker may therefore emit a directory without its
    owner-write bit, which makes a plain ``shutil.rmtree`` fail on POSIX.  Restore
    traversal and owner-write permission only on real directories in this already
    fenced scratch tree, then remove it without following symlinks.
    """

    for current, directories, _files in os.walk(
        path, topdown=True, followlinks=False
    ):
        current_path = Path(current)
        if not current_path.is_symlink():
            current_path.chmod(current_path.stat().st_mode | 0o700)
        for name in directories:
            child = current_path / name
            if not child.is_symlink():
                child.chmod(child.stat().st_mode | 0o700)
    shutil.rmtree(path)


def _projection_entry_fingerprint(
    path: Path, relative: str
) -> tuple[str, str, int]:
    """Fingerprint one regular output root without following symbolic links."""

    if path.is_symlink() or not path.exists():
        raise WorkspaceError(
            f"archive projection output is missing or a symlink: {relative}"
        )
    mode = path.stat().st_mode & 0o777
    if path.is_file():
        return ("file", file_sha256(path), mode)
    if path.is_dir():
        entries = list(path.rglob("*"))
        if any(item.is_symlink() for item in entries):
            raise WorkspaceError(
                f"archive projection output contains a symlink: {relative}"
            )
        if any(not item.is_file() and not item.is_dir() for item in entries):
            raise WorkspaceError(
                f"archive projection output contains a special file: {relative}"
            )
        return ("directory", tree_sha256(path), mode)
    raise WorkspaceError(f"archive projection output is not regular: {relative}")


def _fsync_directory(path: Path) -> None:
    descriptor = _open_for_fsync(path, directory=True)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory_chain(path: Path, stop: Path) -> None:
    current = path.resolve()
    boundary = stop.resolve()
    try:
        current.relative_to(boundary)
    except ValueError as error:
        raise WorkspaceError("durability path escapes the warehouse") from error
    while True:
        _fsync_directory(current)
        if current == boundary:
            return
        current = current.parent


def _fsync_tree(root: Path) -> None:
    directories = [root]
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_symlink():
            raise WorkspaceError(f"artifact candidates may not contain symlinks: {path}")
        if path.is_file():
            descriptor = _open_for_fsync(path)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        elif path.is_dir():
            directories.append(path)
        else:
            raise WorkspaceError(f"artifact candidates must contain only files and directories: {path}")
    for directory in sorted(
        directories, key=lambda item: len(item.relative_to(root).parts), reverse=True
    ):
        _fsync_directory(directory)
