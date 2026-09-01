from __future__ import annotations

import hashlib
import os
import re
import secrets
import tempfile
from pathlib import Path
from typing import Any


RESULT_CHANNEL_ALIAS = ".codex-controller-last-message"
RESULT_ALIAS_DIRECTORY = ".codex-controller-launch"
RESULT_TRANSPORT_DIRECTORY = ".controller-result-channels"
RESULT_CHANNEL_FILENAME = "result.json"
RESULT_CHANNEL_DIRECTORY = re.compile(r"^\.codex-final-[0-9a-f]{64}$")


def lexical_absolute(path: Path) -> Path:
    """Normalize `.`/`..` without following any filesystem link."""

    return Path(os.path.abspath(os.fspath(path)))


def result_channel_contract() -> dict[str, Any]:
    """Return the durable, nonce-free description of result transport."""

    return {
        "schema_version": 3,
        "transport": "outer-cli-parent-held-fixed-alias-inode",
        "launch_namespace": "fixed-alias-only",
        "outer_cli_output_capability": "parent-procfd-readonly-hold",
        "output_descriptor_inherited": False,
        "runtime_fd_stored": False,
        "fixed_alias_stored": True,
        "private_path_stored": False,
        "nonce_stored": False,
        "nonce_hash_stored": False,
        "content_stored_in_provenance": False,
        "post_exit_result_retention": "bounded-redacted-output",
    }


def result_alias_directory(log_dir: Path) -> Path:
    """Return the disclosed launch directory containing only the fixed alias."""

    return lexical_absolute(log_dir) / RESULT_ALIAS_DIRECTORY


def default_result_transport_root(log_dir: Path) -> Path:
    """Return a controller-private root for direct backend callers.

    Production workers use :func:`worker_result_transport_root`.  This fallback
    remains outside the disclosed log/launch ancestry while deterministically
    selecting the same recovery namespace for repeated direct invocations. A
    caller whose logs are on another filesystem must supply an explicit
    same-filesystem channel manifest because the fixed alias is a hard link.
    """

    absolute = lexical_absolute(log_dir)
    identity = hashlib.sha256(str(absolute).encode("utf-8")).hexdigest()
    return (
        lexical_absolute(Path(tempfile.gettempdir()))
        / f".learnfactory-controller-{os.getuid()}"
        / RESULT_TRANSPORT_DIRECTORY
        / identity
    )


def worker_result_transport_root(
    warehouse: Path, *, job_id: str, attempt_number: int
) -> Path:
    """Return the controller-private recovery root for exactly one attempt."""

    if not isinstance(job_id, str) or not job_id:
        raise TypeError("job id must be non-empty text")
    if isinstance(attempt_number, bool) or not isinstance(attempt_number, int):
        raise TypeError("attempt number must be an integer")
    if attempt_number <= 0:
        raise ValueError("attempt number must be positive")
    job_identity = hashlib.sha256(job_id.encode("utf-8")).hexdigest()
    return (
        lexical_absolute(warehouse)
        / RESULT_TRANSPORT_DIRECTORY
        / job_identity
        / f"attempt-{attempt_number:03d}"
    )


def fresh_result_channel(transport_root: Path) -> Path:
    """Mint a fresh runtime-only channel capability beneath an attempt root."""

    return (
        lexical_absolute(transport_root)
        / (".codex-final-" + secrets.token_hex(32))
        / RESULT_CHANNEL_FILENAME
    )


def placeholder_result_channel(log_dir: Path) -> Path:
    """Build a valid but never-created channel for nonce-free provenance."""

    return (
        default_result_transport_root(log_dir)
        / (".codex-final-" + "0" * 64)
        / RESULT_CHANNEL_FILENAME
    )
