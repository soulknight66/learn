from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

from .backends.exec_backend import ExecBackend
from .config import FactorySettings
from .sandbox_policy import (
    build_sandbox_rule_manifest,
    csdiy_examiner_channel_schema,
    is_csdiy_examiner,
)
from .result_channel import RESULT_ALIAS_DIRECTORY, placeholder_result_channel
from .util import FACTORY_EXECUTION_PATHS, canonical_json, redact


SCHEMA = "learnfactory-run-provenance-v3"
_MAX_PATHS = 10_000
_MAX_FILE_BYTES = 16 * 1024 * 1024
_MAX_TOTAL_BYTES = 128 * 1024 * 1024
_URL_USERINFO = re.compile(r"(?i)(https?://)[^/@\s]+@")
_HTTP_URL = re.compile(r"(?i)https?://[^\s<>\"']+")
_SENSITIVE_KEY = re.compile(
    r"(?i)(?:^|[_-])(?:api[_-]?key|authorization|client[_-]?secret|cookie|credential|"
    r"password|private[_-]?key|secret|session[_-]?token|token)(?:$|[_-])"
)
_KNOWN_TOKEN = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:"
    r"github_pat_[A-Za-z0-9_]{16,}|"
    r"gh[pousr]_[A-Za-z0-9]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"AKIA[A-Z0-9]{16}"
    r")(?![A-Za-z0-9])"
)
_CREDENTIAL_PROSE = re.compile(
    r"(?i)\b(api[_-]?key|authorization|client[_-]?secret|credential|password|"
    r"private[_-]?key|secret|token)(\s+(?:is|was)\s+)([^\s,;]+)"
)
_SAFE_MODEL_ID = re.compile(r"^(?:gpt|o)[A-Za-z0-9._:/-]{0,127}$")
_SAFE_REASONING = frozenset({"low", "medium", "high", "xhigh", "max", "ultra"})
_OMITTED_PROVIDER_NAME = "<external-provider-name-omitted>"
_OMITTED_EXTERNAL_VALUE = "<external-value-omitted>"
_CLI_EXECUTABLE = "<cli-executable>"
_CODEX_HOME = "<codex-home>"
_WORKSPACE = "<workspace>"
_LOG_DIR = "<log-dir>"
_LAUNCH_DIR = f"{_LOG_DIR}/{RESULT_ALIAS_DIRECTORY}"


@dataclass(frozen=True)
class RunProvenance:
    digest: str
    metadata: dict[str, Any]


def unavailable_run_provenance(error: BaseException) -> RunProvenance:
    """Return a secret-safe failure record instead of omitting a run.

    Exception messages are deliberately excluded.  An exception raised while
    handling configuration or a payload may quote the value that caused it, and
    pattern-based redaction cannot prove an opaque credential is absent.
    """

    components = {
        "code_sha256": None,
        "safe_configuration_sha256": None,
        "safe_policy_sha256": None,
        "safe_invocation_sha256": None,
    }
    digest = _sha256_json(
        {"schema": SCHEMA, "status": "CAPTURE_FAILED", "components": components}
    )
    return RunProvenance(
        digest=digest,
        metadata={
            "schema": SCHEMA,
            "status": "CAPTURE_FAILED",
            "fingerprint_sha256": digest,
            "components": components,
            "error": {
                "type": _safe_type_name(error),
                "message_stored": False,
            },
            "binding": _binding_boundary(),
            "secret_boundary": (
                "The exception message, configuration, payload, and environment are excluded."
            ),
        },
    )


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _safe_type_name(error: BaseException) -> str:
    rendered = type(error).__name__
    return rendered if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", rendered) else "Exception"


def _binding_boundary() -> dict[str, Any]:
    return {
        "scope": "safe-execution-envelope",
        "exactness": (
            "Exact for recorded, non-secret execution fields and CLI bytes. Credential-bearing "
            "material is deterministically redacted or structurally omitted before hashing."
        ),
        "excluded_without_hashing": [
            "authentication material",
            "environment values",
            "provider display names",
            "URL userinfo, query, and fragment components",
        ],
    }


def _sanitize_url(value: str) -> tuple[str, bool]:
    """Remove URL components that commonly transport credentials.

    The scheme, host, port, and path identify the safe endpoint envelope.  URL
    userinfo, query parameters, and fragments are neither retained nor hashed.
    """

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except (TypeError, ValueError):
        return _OMITTED_EXTERNAL_VALUE, True
    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        return _OMITTED_EXTERNAL_VALUE, True
    host = hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if port is not None:
        host = f"{host}:{port}"
    sanitized = urlunsplit(
        SplitResult(parsed.scheme.lower(), host, parsed.path, "", "")
    )
    changed = (
        "@" in parsed.netloc
        or bool(parsed.query)
        or bool(parsed.fragment)
        or sanitized != value
    )
    return sanitized, changed


def _sanitize_text(value: str) -> tuple[str, int]:
    """Return deterministic text safe enough to persist and hash."""

    rendered = redact(value, limit=None)
    redactions = int(rendered != value)
    without_known_tokens = _KNOWN_TOKEN.sub("<redacted-token>", rendered)
    if without_known_tokens != rendered:
        redactions += 1
        rendered = without_known_tokens
    without_prose = _CREDENTIAL_PROSE.sub(r"\1\2<redacted>", rendered)
    if without_prose != rendered:
        redactions += 1
        rendered = without_prose

    def replace_url(match: re.Match[str]) -> str:
        nonlocal redactions
        safe_url, changed = _sanitize_url(match.group(0))
        if changed:
            redactions += 1
        return safe_url

    rendered = _HTTP_URL.sub(replace_url, rendered)
    # This narrower fallback covers malformed URLs that urlsplit could not
    # safely interpret without ever retaining the userinfo itself.
    without_userinfo = _URL_USERINFO.sub(r"\1<redacted>@", rendered)
    if without_userinfo != rendered:
        redactions += 1
        rendered = without_userinfo
    return rendered, redactions


def _sanitize_binding_value(value: Any) -> tuple[Any, int]:
    """Redact credential-bearing JSON material before it is ever hashed."""

    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, list):
        safe_items: list[Any] = []
        redactions = 0
        for item in value:
            safe_item, count = _sanitize_binding_value(item)
            safe_items.append(safe_item)
            redactions += count
        return safe_items, redactions
    if isinstance(value, tuple):
        return _sanitize_binding_value(list(value))
    if isinstance(value, dict):
        safe_mapping: dict[str, Any] = {}
        redactions = 0
        for key, item in value.items():
            rendered_key, key_redactions = _sanitize_text(str(key))
            redactions += key_redactions
            if _SENSITIVE_KEY.search(rendered_key):
                safe_mapping[rendered_key] = "<redacted-sensitive-field>"
                redactions += 1
                continue
            safe_item, count = _sanitize_binding_value(item)
            safe_mapping[rendered_key] = safe_item
            redactions += count
        return safe_mapping, redactions
    return value, 0


def _binding_fingerprint(value: Any) -> dict[str, Any]:
    safe_value, redactions = _sanitize_binding_value(value)
    return {
        "sha256": _sha256_json(safe_value),
        "binding_scope": "safe-redacted-envelope" if redactions else "exact",
        "redaction_count": redactions,
        "content_stored": False,
    }


def _secret_safe(value: Any) -> Any:
    """Final defensive redaction for values selected for persistence."""

    return _sanitize_binding_value(value)[0]


def _frame(digest: Any, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    # These are background, read-only provenance queries. On a large NFS
    # worktree Git may otherwise take an index-refresh lock and leave
    # index.lock behind if our bounded timeout terminates the query. The
    # config override protects the operated Git 2.9 client; the environment
    # guard covers newer clients with the optional-locks facility.
    environment["GIT_OPTIONAL_LOCKS"] = "0"
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
        env=environment,
        timeout=10,
        check=False,
    )


def _decode_paths(raw: bytes) -> list[str]:
    if not raw:
        return []
    values = raw.split(b"\0")
    if values[-1] == b"":
        values.pop()
    result: list[str] = []
    for value in values:
        rendered = value.decode("utf-8", errors="strict")
        pure = PurePosixPath(rendered)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise ValueError(f"Git returned an unsafe path: {rendered!r}")
        result.append(pure.as_posix())
    return sorted(set(result))


def _hash_selected_files(root: Path, paths: list[str], *, domain: bytes) -> dict[str, Any]:
    digest = hashlib.sha256()
    digest.update(b"learnfactory-run-code-v1\0" + domain + b"\0")
    total_bytes = 0
    hashed_bytes = 0
    omitted: list[str] = []
    raced: list[str] = []
    original_path_count = len(paths)
    if original_path_count > _MAX_PATHS:
        omitted.extend(paths[_MAX_PATHS:])
        paths = paths[:_MAX_PATHS]
    for relative in paths:
        target = root / relative
        encoded_path = relative.encode("utf-8")
        try:
            before = target.lstat()
        except OSError:
            digest.update(b"M")
            _frame(digest, encoded_path)
            continue
        mode = stat.S_IMODE(before.st_mode)
        total_bytes += before.st_size if stat.S_ISREG(before.st_mode) else 0
        if stat.S_ISLNK(before.st_mode):
            digest.update(b"L")
            _frame(digest, encoded_path)
            _frame(digest, os.fsencode(os.readlink(target)))
        elif stat.S_ISREG(before.st_mode):
            digest.update(b"F")
            _frame(digest, encoded_path)
            _frame(digest, mode.to_bytes(4, "big"))
            _frame(digest, before.st_size.to_bytes(8, "big"))
            if (
                before.st_size > _MAX_FILE_BYTES
                or hashed_bytes + before.st_size > _MAX_TOTAL_BYTES
            ):
                digest.update(b"BOUNDED")
                omitted.append(relative)
            else:
                content_digest = hashlib.sha256()
                with target.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        content_digest.update(chunk)
                _frame(digest, content_digest.digest())
                hashed_bytes += before.st_size
        elif stat.S_ISDIR(before.st_mode):
            digest.update(b"D")
            _frame(digest, encoded_path)
            _frame(digest, mode.to_bytes(4, "big"))
        else:
            digest.update(b"S")
            _frame(digest, encoded_path)
            _frame(digest, before.st_mode.to_bytes(8, "big"))
            omitted.append(relative)
        try:
            after = target.lstat()
        except OSError:
            raced.append(relative)
        else:
            if (
                before.st_dev,
                before.st_ino,
                before.st_mode,
                before.st_size,
                before.st_mtime_ns,
            ) != (
                after.st_dev,
                after.st_ino,
                after.st_mode,
                after.st_size,
                after.st_mtime_ns,
            ):
                raced.append(relative)
    return {
        "sha256": digest.hexdigest(),
        "path_count": original_path_count,
        "total_regular_bytes": total_bytes,
        "hashed_regular_bytes": hashed_bytes,
        "status": "RACED" if raced else "BOUNDED" if omitted else "COMPLETE",
        "omitted_path_count": len(set(omitted)),
        "raced_paths": sorted(set(raced))[:100],
    }


def _repository_snapshot(root: Path) -> dict[str, Any]:
    scope = list(FACTORY_EXECUTION_PATHS)
    try:
        revision = _git(root, "rev-parse", "HEAD")
        if revision.returncode != 0:
            return {
                "status": "UNVERSIONED",
                "commit": None,
                "scope": scope,
                "error": {
                    "operation": "rev-parse",
                    "detail_stored": False,
                },
            }
        tracked_result = _git(root, "ls-files", "-z", "--", *scope)
        untracked_result = _git(
            root, "ls-files", "-z", "--others", "--exclude-standard", "--", *scope
        )
        dirty_result = _git(root, "diff", "--name-only", "-z", "HEAD", "--", *scope)
        for label, result in (
            ("tracked", tracked_result),
            ("untracked", untracked_result),
            ("dirty", dirty_result),
        ):
            if result.returncode != 0:
                return {
                    "status": "GIT_QUERY_FAILED",
                    "commit": revision.stdout.decode("ascii", "replace").strip(),
                    "scope": scope,
                    "query": label,
                    "error": {
                        "operation": "git-query",
                        "detail_stored": False,
                    },
                }
        tracked = _decode_paths(tracked_result.stdout)
        untracked = _decode_paths(untracked_result.stdout)
        dirty = _decode_paths(dirty_result.stdout)
        tracked_hash = _hash_selected_files(root, tracked, domain=b"tracked")
        untracked_hash = _hash_selected_files(root, untracked, domain=b"untracked")
        combined = _sha256_json(
            {
                "schema": "learnfactory-execution-tree-v2",
                "commit": revision.stdout.decode("ascii", "replace").strip(),
                "tracked": tracked_hash["sha256"],
                "untracked": untracked_hash["sha256"],
            }
        )
        status = "RECORDED"
        if tracked_hash["status"] != "COMPLETE" or untracked_hash["status"] != "COMPLETE":
            status = "PARTIAL"
        return {
            "status": status,
            "commit": revision.stdout.decode("ascii", "replace").strip(),
            "root": "<factory-root>",
            "scope": scope,
            "execution_tree_sha256": combined,
            "tracked": tracked_hash,
            "untracked": untracked_hash,
            "tracked_worktree_clean": not dirty,
            "dirty_tracked_paths": dirty,
            "untracked_paths": untracked,
            "limitations": (
                "Only execution-relevant, Git-tracked or non-ignored untracked paths in scope are "
                "hashed; warehouse, reports, tests, arbitrary external config fields, and ignored "
                "files are excluded. File contents are never stored."
            ),
        }
    except (OSError, UnicodeError, ValueError, subprocess.SubprocessError) as error:
        return {
            "status": "UNAVAILABLE",
            "commit": None,
            "scope": scope,
            "error": {
                "type": _safe_type_name(error),
                "detail_stored": False,
            },
        }


def _safe_local_path(path: Path | None, root: Path) -> str | None:
    if path is None:
        return None
    try:
        relative = path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except (OSError, ValueError):
        return "<external-path-omitted>"
    return f"<factory-root>/{relative.as_posix()}"


def _safe_url_record(value: str | None) -> dict[str, Any]:
    if not value:
        return {
            "configured": False,
            "safe_endpoint": None,
            "binding_scope": "exact",
        }
    safe_endpoint, changed = _sanitize_url(value)
    try:
        parsed = urlsplit(value)
        has_userinfo = "@" in parsed.netloc
        has_query = bool(parsed.query)
        has_fragment = bool(parsed.fragment)
    except (TypeError, ValueError):
        has_userinfo = has_query = has_fragment = False
        changed = True
    return {
        "configured": True,
        "safe_endpoint": safe_endpoint,
        "binding_scope": "sanitized-endpoint" if changed else "exact",
        "userinfo_omitted": has_userinfo,
        "query_omitted": has_query,
        "fragment_omitted": has_fragment,
    }


def _safe_model(value: str | None) -> str | None:
    if value is None:
        return None
    return value if _SAFE_MODEL_ID.fullmatch(value) else "<external-model-id-omitted>"


def _safe_reasoning(value: str | None) -> str | None:
    if value is None:
        return None
    return value if value in _SAFE_REASONING else "<external-reasoning-value-omitted>"


def _cli_binary_identity(executable: Path) -> dict[str, Any]:
    """Hash the resolved CLI bytes without retaining its environment-derived path."""

    try:
        before = executable.stat()
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("resolved CLI is not a regular file")
        digest = hashlib.sha256()
        with executable.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        after = executable.stat()
        raced = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
        )
        return {
            "status": "RACED" if raced else "RECORDED",
            "sha256": digest.hexdigest(),
            "bytes": before.st_size,
            "executable_mode": stat.S_IMODE(before.st_mode),
            "resolved_path_stored": False,
        }
    except (OSError, ValueError) as error:
        return {
            "status": "UNAVAILABLE",
            "sha256": None,
            "resolved_path_stored": False,
            "error": {
                "type": _safe_type_name(error),
                "detail_stored": False,
            },
        }


def _safe_configuration(
    settings: FactorySettings,
    *,
    effective_model: str | None,
    effective_reasoning: str | None,
) -> dict[str, Any]:
    """Return only allowlisted operational values; never copy raw TOML or environment."""

    return {
        "config_path": _safe_local_path(settings.config_path, settings.root),
        "factory": {
            "database": _safe_local_path(settings.database, settings.root),
            "warehouse": _safe_local_path(settings.warehouse, settings.root),
            "lease_seconds": settings.lease_seconds,
            "heartbeat_seconds": settings.heartbeat_seconds,
            "database_busy_timeout_seconds": (
                settings.database_busy_timeout_seconds
            ),
            "poll_seconds": settings.poll_seconds,
            "max_concurrency": settings.max_concurrency,
            "allow_host_command_validators": settings.allow_host_command_validators,
            "course_revision_limit": settings.course_revision_limit,
            "shutdown_grace_seconds": settings.shutdown_grace_seconds,
            "limits": dict(sorted(settings.limits.items())),
            "retry_base_seconds": settings.retry_base_seconds,
            "retry_max_seconds": settings.retry_max_seconds,
        },
        "backend": {
            "name": settings.backend.name,
            "command": _CLI_EXECUTABLE,
            "permission_profile": settings.backend.permission_profile,
            "toolchain_read_roots": {
                "count": len(settings.backend.toolchain_read_roots),
                "values_stored": False,
            },
            "timeout_seconds": settings.backend.timeout_seconds,
            "configured_model": _safe_model(settings.backend.model),
            "configured_reasoning_effort": _safe_reasoning(
                settings.backend.reasoning_effort
            ),
            "effective_model": _safe_model(effective_model),
            "effective_reasoning_effort": _safe_reasoning(effective_reasoning),
            "provider": settings.backend.provider,
            "provider_name": {
                "configured": settings.backend.provider_name is not None,
                "value": (
                    _OMITTED_PROVIDER_NAME
                    if settings.backend.provider_name is not None
                    else settings.backend.provider
                ),
                "configured_value_stored": False,
            },
            "base_url": _safe_url_record(settings.backend.base_url),
            "requires_openai_auth": settings.backend.requires_openai_auth,
            "supports_websockets": settings.backend.supports_websockets,
            "wire_api": "responses" if settings.backend.name == "exec" else None,
            "external_auth_material": {
                "stored": False,
                "hashed": False,
                "source": "operator process boundary",
            },
        },
        "selection_policy": (
            "Allowlisted parsed values only. External paths, provider display names, URL credential "
            "components, raw TOML, environment values, and credentials are not stored or hashed."
        ),
    }


def _job_policy(
    *,
    job_id: str,
    job_type: str,
    worker_type: str,
    payload: dict[str, Any],
    dependency_job_ids: list[str],
) -> dict[str, Any]:
    seed_policy = payload.get("seed_policy")
    safe_seed_policy: dict[str, Any] | None = None
    if isinstance(seed_policy, dict):
        safe_seed_policy = {
            key: seed_policy[key]
            for key in ("kind", "version", "role")
            if isinstance(seed_policy.get(key), (str, int, float, bool))
        }
    validators = payload.get("validators", [])
    payload_fingerprint = _binding_fingerprint(payload)
    validator_fingerprint = _binding_fingerprint(validators)
    safe_seed_policy = _secret_safe(safe_seed_policy)
    safe_artifact_contract = _secret_safe(
        {
            key: payload.get(key)
            for key in ("artifact_type", "artifact_path", "validation_status")
            if isinstance(payload.get(key), (str, list))
        }
    )
    return {
        "job_id": job_id,
        "job_type": job_type,
        "worker_type": worker_type,
        "payload_sha256": payload_fingerprint["sha256"],
        "payload_binding_scope": payload_fingerprint["binding_scope"],
        "payload_redaction_count": payload_fingerprint["redaction_count"],
        "validator_policy_sha256": validator_fingerprint["sha256"],
        "validator_policy_binding_scope": validator_fingerprint["binding_scope"],
        "validator_policy_redaction_count": validator_fingerprint[
            "redaction_count"
        ],
        "validator_count": len(validators) if isinstance(validators, list) else None,
        "dependency_job_ids": sorted(set(dependency_job_ids)),
        "seed_policy": safe_seed_policy,
        "artifact_contract": safe_artifact_contract,
        "payload_policy": (
            "Credential-free payload fields are bound exactly. Detected credential material is "
            "redacted before hashing, and payload contents are not duplicated here."
        ),
    }


def _normalized_invocation(invocation: dict[str, Any], workspace: Path, log_dir: Path) -> dict[str, Any]:
    """Remove run-local absolute paths from the persisted comparable envelope."""

    replacements = {
        str(workspace): _WORKSPACE,
        str(log_dir): _LOG_DIR,
    }

    def normalize(value: Any) -> Any:
        if isinstance(value, str):
            rendered = value
            for old, new in replacements.items():
                rendered = rendered.replace(old, new)
            return rendered
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        return value

    return normalize(invocation)


def _safe_config_argument(
    value: str,
    settings: FactorySettings,
    *,
    replacements: list[tuple[str, str]],
) -> str:
    key, separator, _raw_value = value.partition("=")
    provider_prefix = (
        f"model_providers.{settings.backend.provider}"
        if settings.backend.provider
        else None
    )
    if separator and provider_prefix and key == f"{provider_prefix}.name":
        safe_name = (
            _OMITTED_PROVIDER_NAME
            if settings.backend.provider_name is not None
            else settings.backend.provider
        )
        return f"{key}={json.dumps(safe_name, ensure_ascii=False)}"
    if separator and (
        key == "openai_base_url"
        or (provider_prefix and key == f"{provider_prefix}.base_url")
    ):
        safe_endpoint = _safe_url_record(settings.backend.base_url)["safe_endpoint"]
        return f"{key}={json.dumps(safe_endpoint, ensure_ascii=False)}"
    if separator and key == "model_reasoning_effort":
        try:
            reasoning_value = json.loads(_raw_value)
        except json.JSONDecodeError:
            reasoning_value = None
        safe_reasoning = _safe_reasoning(
            reasoning_value if isinstance(reasoning_value, str) else None
        )
        return f"{key}={json.dumps(safe_reasoning, ensure_ascii=False)}"

    rendered = value
    for raw, marker in replacements:
        if raw:
            rendered = rendered.replace(raw, marker)
    return _sanitize_text(rendered)[0]


def _safe_argv(
    argv: list[Any],
    settings: FactorySettings,
    *,
    executable: Path,
    workspace: Path,
    log_dir: Path,
) -> list[Any]:
    try:
        codex_home = Path(
            os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
        ).resolve(strict=False)
    except OSError:
        codex_home = Path("/__unavailable_codex_home__")
    replacements = [
        (str(workspace), _WORKSPACE),
        (str(log_dir), _LOG_DIR),
        (str(executable), _CLI_EXECUTABLE),
        (str(codex_home), _CODEX_HOME),
    ]
    replacements.extend(
        (raw, f"<toolchain-root-{index}>")
        for index, raw in enumerate(settings.backend.toolchain_read_roots, start=1)
    )
    replacements.sort(key=lambda item: len(item[0]), reverse=True)

    safe: list[Any] = []
    previous: str | None = None
    for index, item in enumerate(argv):
        if not isinstance(item, str):
            safe.append(item)
            previous = None
            continue
        if index == 0:
            safe.append(_CLI_EXECUTABLE)
        elif previous == "--config":
            safe.append(
                _safe_config_argument(item, settings, replacements=replacements)
            )
        elif previous == "--model":
            safe.append(_safe_model(item))
        else:
            rendered = item
            for raw, marker in replacements:
                if raw:
                    rendered = rendered.replace(raw, marker)
            safe.append(_sanitize_text(rendered)[0])
        previous = item
    return safe


def _safe_invocation_manifest(
    manifest: dict[str, Any],
    settings: FactorySettings,
    *,
    executable: Path,
    workspace: Path,
    log_dir: Path,
) -> dict[str, Any]:
    safe = dict(manifest)
    raw_argv = manifest.get("argv", [])
    safe["argv"] = _safe_argv(
        raw_argv if isinstance(raw_argv, list) else [],
        settings,
        executable=executable,
        workspace=workspace,
        log_dir=log_dir,
    )
    sandbox_rules = manifest.get("sandbox_rules")
    tools_enabled = not (
        isinstance(sandbox_rules, dict)
        and sandbox_rules.get("tools_enabled") is False
    )
    safe["cwd"] = _WORKSPACE if tools_enabled else _LAUNCH_DIR
    safe["model"] = _safe_model(manifest.get("model"))
    safe["reasoning_effort"] = _safe_reasoning(manifest.get("reasoning_effort"))
    raw_toolchain_roots = manifest.get("toolchain_read_roots")
    effective_count = (
        len(raw_toolchain_roots) if isinstance(raw_toolchain_roots, list) else 0
    )
    safe["toolchain_read_roots"] = {
        "count": effective_count,
        "configured_count": len(settings.backend.toolchain_read_roots),
        "values_stored": False,
    }
    safe["cli_binary"] = _cli_binary_identity(executable)
    safe["external_auth_material"] = {
        "stored": False,
        "hashed": False,
        "boundary": "operator process",
    }
    return _normalized_invocation(_secret_safe(safe), workspace, log_dir)


def _invocation(
    settings: FactorySettings,
    *,
    job_type: str,
    worker_type: str,
    payload: dict[str, Any],
    workspace: Path,
    log_dir: Path,
    effective_model: str | None,
    effective_reasoning: str | None,
) -> dict[str, Any]:
    if job_type != "codex_task":
        return {
            "schema_version": 1,
            "status": "RECORDED",
            "backend": "in-process-handler",
            "handler_job_type": job_type,
            "cwd": _WORKSPACE,
            "model": None,
            "reasoning_effort": None,
            "binding_scope": "safe-execution-envelope",
        }
    prompt = str(payload.get("prompt", "")).strip()
    safe_prompt, prompt_redactions = _sanitize_text(prompt)
    prompt_binding_scope = (
        "safe-redacted-envelope" if prompt_redactions else "exact"
    )
    output_schema = payload.get("output_schema")
    if output_schema and is_csdiy_examiner(worker_type, payload):
        output_schema = csdiy_examiner_channel_schema(output_schema)
    schema_path = log_dir / "response-schema.json" if output_schema else None
    timeout = float(payload.get("timeout_seconds", settings.backend.timeout_seconds))
    backend = ExecBackend(
        settings.backend.command,
        timeout_seconds=settings.backend.timeout_seconds,
        permission_profile=settings.backend.permission_profile,
        toolchain_read_roots=settings.backend.toolchain_read_roots,
        provider=settings.backend.provider,
        base_url=settings.backend.base_url,
        provider_name=settings.backend.provider_name,
        requires_openai_auth=settings.backend.requires_openai_auth,
        supports_websockets=settings.backend.supports_websockets,
    )
    tools_enabled = not is_csdiy_examiner(worker_type, payload)
    try:
        # Provenance describes the nonce-free transport contract. The concrete
        # randomized capability exists only in the worker/backend runtime.
        channel = placeholder_result_channel(log_dir)
        sandbox_manifest = build_sandbox_rule_manifest(
            workspace=workspace,
            log_dir=log_dir,
            worker_type=worker_type,
            payload=payload,
            result_channel=channel,
        )
        tools_enabled = sandbox_manifest.tools_enabled
        raw_manifest = backend.invocation_manifest(
            workspace,
            prompt=safe_prompt,
            output_schema=schema_path,
            model=effective_model,
            reasoning_effort=effective_reasoning,
            timeout_seconds=timeout,
            sandbox_manifest=sandbox_manifest,
        )
        raw_argv = raw_manifest.get("argv", [])
        if not isinstance(raw_argv, list) or not raw_argv or not isinstance(raw_argv[0], str):
            raise ValueError("invocation manifest did not identify the CLI executable")
        manifest = _safe_invocation_manifest(
            raw_manifest,
            settings,
            executable=Path(raw_argv[0]),
            workspace=workspace,
            log_dir=log_dir,
        )
        manifest["status"] = "RECORDED"
    except (OSError, TypeError, ValueError) as error:
        manifest = {
            "schema_version": 1,
            "backend": settings.backend.name,
            "status": "UNAVAILABLE",
            "command": _CLI_EXECUTABLE,
            "cwd": _WORKSPACE,
            "timeout_seconds": timeout,
            "model": _safe_model(effective_model),
            "reasoning_effort": _safe_reasoning(effective_reasoning),
            "permission_profile": settings.backend.permission_profile,
            "toolchain_read_roots": {
                "count": len(settings.backend.toolchain_read_roots),
                "values_stored": False,
            },
            "error": {
                "type": _safe_type_name(error),
                "detail_stored": False,
            },
        }
    if "prompt" not in manifest:
        try:
            prompt_record = backend.prompt_manifest(
                safe_prompt, tools_enabled=tools_enabled
            )
        except (TypeError, ValueError):
            prompt_record = {
                "effective_prompt": {
                    "sha256": None,
                    "utf8_bytes": None,
                    "content_stored": False,
                    "status": "INVALID",
                },
                "job_prompt": {
                    "sha256": hashlib.sha256(safe_prompt.encode("utf-8")).hexdigest(),
                    "utf8_bytes": len(safe_prompt.encode("utf-8")),
                    "content_stored": False,
                },
                "leaf_worker_policy": {
                    "sha256": None,
                    "utf8_bytes": None,
                    "content_stored": False,
                    "status": "UNAVAILABLE",
                },
            }
        manifest["prompt"] = prompt_record["effective_prompt"]
        manifest["job_prompt"] = prompt_record["job_prompt"]
        manifest["leaf_worker_policy"] = prompt_record["leaf_worker_policy"]
    for key in ("prompt", "job_prompt"):
        manifest[key]["binding_scope"] = prompt_binding_scope
        manifest[key]["redaction_count"] = prompt_redactions
    manifest["binding_scope"] = "safe-execution-envelope"
    output_schema_fingerprint = _binding_fingerprint(output_schema)
    manifest["output_schema"] = {
        "present": bool(output_schema),
        "sha256": (
            output_schema_fingerprint["sha256"] if output_schema else None
        ),
        "binding_scope": (
            output_schema_fingerprint["binding_scope"] if output_schema else "exact"
        ),
        "redaction_count": (
            output_schema_fingerprint["redaction_count"] if output_schema else 0
        ),
        "content_stored": False,
    }
    return _normalized_invocation(_secret_safe(manifest), workspace, log_dir)


def capture_run_provenance(
    settings: FactorySettings,
    *,
    job_id: str,
    job_type: str,
    worker_type: str,
    payload: dict[str, Any],
    dependency_job_ids: list[str],
    workspace: Path,
    log_dir: Path,
    effective_model: str | None,
    effective_reasoning: str | None,
) -> RunProvenance:
    """Capture a deterministic, secret-safe start-time execution envelope."""

    repository = _secret_safe(_repository_snapshot(settings.root))
    configuration = _secret_safe(
        _safe_configuration(
            settings,
            effective_model=effective_model,
            effective_reasoning=effective_reasoning,
        )
    )
    policy = _secret_safe(
        _job_policy(
            job_id=job_id,
            job_type=job_type,
            worker_type=worker_type,
            payload=payload,
            dependency_job_ids=dependency_job_ids,
        )
    )
    invocation = _secret_safe(
        _invocation(
            settings,
            job_type=job_type,
            worker_type=worker_type,
            payload=payload,
            workspace=workspace,
            log_dir=log_dir,
            effective_model=effective_model,
            effective_reasoning=effective_reasoning,
        )
    )
    components = {
        "code_sha256": repository.get("execution_tree_sha256"),
        "safe_configuration_sha256": _sha256_json(configuration),
        "safe_policy_sha256": _sha256_json(policy),
        "safe_invocation_sha256": _sha256_json(
            _normalized_invocation(invocation, workspace, log_dir)
        ),
    }
    capture_status = "RECORDED"
    if repository.get("status") != "RECORDED" or invocation.get("status") != "RECORDED":
        capture_status = "PARTIAL"
    cli_binary = invocation.get("cli_binary")
    if isinstance(cli_binary, dict) and cli_binary.get("status") != "RECORDED":
        capture_status = "PARTIAL"
    digest = _sha256_json(
        {"schema": SCHEMA, "status": capture_status, "components": components}
    )
    metadata = {
        "schema": SCHEMA,
        "status": capture_status,
        "fingerprint_sha256": digest,
        "components": components,
        "repository": repository,
        "configuration": configuration,
        "policy": policy,
        "invocation": invocation,
        "binding": _binding_boundary(),
        "secret_boundary": (
            "Raw config, prompt text, payload text, environment values, authentication material, "
            "URL credential components, provider display names, and file contents are not stored. "
            "Environment and authentication material are also excluded before envelope hashing; "
            "credential-free prompt and payload fields retain exact digests."
        ),
    }
    return RunProvenance(digest=digest, metadata=metadata)


def write_run_provenance(log_dir: Path, record: RunProvenance) -> Path:
    """Durably publish a human-readable copy beside bounded worker logs."""

    log_dir.mkdir(parents=True, exist_ok=True)
    destination = log_dir / "RUN_PROVENANCE.json"
    data = (json.dumps(record.metadata, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".RUN_PROVENANCE.", suffix=".tmp", dir=log_dir
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            view = memoryview(data)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("short write while persisting run provenance")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, destination)
        temporary = None
        directory = os.open(log_dir, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    return destination
