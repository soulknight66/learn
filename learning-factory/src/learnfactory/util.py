from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any


FACTORY_EXECUTION_PATHS = (
    "src",
    "migrations",
    "scripts",
    "prompts",
    "skills",
    "pyproject.toml",
)


def now() -> float:
    return time.time()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def json_value(raw: str | None, default: Any) -> Any:
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(token|api[_-]?key|secret|password)(\s*[=:]\s*)([^\s,;]+)"
)
_JSON_SECRET_DOUBLE = re.compile(
    r'(?i)("(?:token|api[_-]?key|secret|password)"\s*:\s*)"(?:\\.|[^"\\])*"'
)
_JSON_SECRET_SINGLE = re.compile(
    r"(?i)('(?:token|api[_-]?key|secret|password)'\s*:\s*)'(?:\\.|[^'\\])*'"
)
_OPENAI_KEY = re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b")
_AUTH_ERROR_KEY = re.compile(r"(?i)(incorrect api key provided:\s*)[^\s,;]+")
_BEARER = re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s,;]+")
_RUNTIME_PROC_FD = re.compile(r"/proc/[1-9][0-9]*/fd/[0-9]+")


def redact(text: str, limit: int | None = 20_000) -> str:
    """Remove common inline credential assignments before persistence."""
    clean = _JSON_SECRET_DOUBLE.sub(r'\1"<redacted>"', text)
    clean = _JSON_SECRET_SINGLE.sub(r"\1'<redacted>'", clean)
    clean = _SECRET_ASSIGNMENT.sub(r"\1\2<redacted>", clean)
    clean = _OPENAI_KEY.sub("<redacted-api-key>", clean)
    clean = _AUTH_ERROR_KEY.sub(r"\1<redacted>", clean)
    clean = _BEARER.sub(r"\1<redacted>", clean)
    clean = _RUNTIME_PROC_FD.sub("<redacted-runtime-fd-capability>", clean)
    if limit is not None and len(clean) > limit:
        return clean[:limit] + "\n<truncated>"
    return clean


def slugify(value: str) -> str:
    value = value.strip().lower().replace("&", " and ")
    value = re.sub(r"[^\w\-]+", "-", value, flags=re.UNICODE)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "item"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_revision(root: Path) -> dict[str, Any]:
    """Return bounded Git provenance for the code that produced an artifact."""

    # Git 2.9 predates optional locks, so also disable its legacy diff refresh.
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"

    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "git",
                "-c",
                "diff.autoRefreshIndex=false",
                "-C",
                str(root),
                *arguments,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
            timeout=5,
            check=False,
        )

    try:
        revision = run("rev-parse", "HEAD")
    except (OSError, subprocess.SubprocessError) as error:
        return {
            "commit": None,
            "tracked_worktree_clean": False,
            "status": "UNAVAILABLE",
            "error": redact(str(error), limit=500),
        }
    if revision.returncode != 0:
        return {
            "commit": None,
            "tracked_worktree_clean": False,
            "status": "UNVERSIONED",
            "error": redact(revision.stderr, limit=500).strip(),
        }

    commit = revision.stdout.strip()
    try:
        dirty = run(
            "diff",
            "--name-only",
            "HEAD",
            "--",
            *FACTORY_EXECUTION_PATHS,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return {
            "commit": commit,
            "tracked_worktree_clean": False,
            "status": "STATUS_UNAVAILABLE",
            "error": redact(str(error), limit=500),
        }
    if dirty.returncode != 0:
        return {
            "commit": commit,
            "tracked_worktree_clean": False,
            "status": "STATUS_UNAVAILABLE",
            "error": redact(dirty.stderr, limit=500).strip(),
        }
    return {
        "commit": commit,
        "tracked_worktree_clean": not bool(dirty.stdout.strip()),
        "status": "RECORDED",
    }


def tree_sha256_v1(root: Path) -> str:
    """Legacy unframed tree hash retained only to verify pre-v2 artifacts."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        if path.is_symlink():
            digest.update(b"L")
            digest.update(path.readlink().as_posix().encode("utf-8"))
        elif path.is_file():
            digest.update(b"F")
            digest.update(oct(path.stat().st_mode & 0o777).encode("ascii"))
            digest.update(bytes.fromhex(file_sha256(path)))
        elif path.is_dir():
            digest.update(b"D")
    return digest.hexdigest()


def _hash_field(digest: "hashlib._Hash", value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def tree_sha256(root: Path) -> str:
    """Hash a tree with versioned, length-framed structural records."""

    digest = hashlib.sha256()
    digest.update(b"learnfactory-tree-sha256-v2\0")
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        if path.is_symlink():
            digest.update(b"L")
            _hash_field(digest, relative)
            _hash_field(digest, os.fsencode(path.readlink()))
        elif path.is_file():
            digest.update(b"F")
            _hash_field(digest, relative)
            _hash_field(digest, (path.stat().st_mode & 0o777).to_bytes(4, "big"))
            _hash_field(digest, bytes.fromhex(file_sha256(path)))
        elif path.is_dir():
            digest.update(b"D")
            _hash_field(digest, relative)
    return digest.hexdigest()


def tree_sha256_for_algorithm(root: Path, algorithm: str) -> str:
    if algorithm == "tree-sha256-v2":
        return tree_sha256(root)
    if algorithm == "tree-sha256-v1":
        return tree_sha256_v1(root)
    raise ValueError(f"unsupported tree checksum algorithm: {algorithm}")
