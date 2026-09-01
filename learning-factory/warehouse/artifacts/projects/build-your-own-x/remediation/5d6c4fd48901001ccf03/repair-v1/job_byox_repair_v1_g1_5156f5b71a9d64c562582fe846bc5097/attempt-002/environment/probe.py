#!/usr/bin/env python3
"""Print a bounded, non-grading report about optional Minibox prerequisites."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
from typing import Any


_NAMESPACE_ENTRIES = {
    "user": "user",
    "mount": "mnt",
    "pid": "pid",
    "uts": "uts",
    "ipc": "ipc",
    "net": "net",
}

_KERNEL_SETTINGS = {
    "max_user_namespaces": Path("/proc/sys/user/max_user_namespaces"),
    "unprivileged_userns_clone": Path(
        "/proc/sys/kernel/unprivileged_userns_clone"
    ),
}


def _kernel_setting(path: Path) -> dict[str, Any]:
    """Read one small procfs setting without treating absence as failure."""

    try:
        raw = path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError) as exc:
        return {
            "available": False,
            "path": str(path),
            "reason": type(exc).__name__,
            "value": None,
        }

    try:
        value: int | str = int(raw, 10)
    except ValueError:
        value = raw[:128]
    return {
        "available": True,
        "path": str(path),
        "reason": None,
        "value": value,
    }


def _bounded_text(data: bytes, limit: int = 1000) -> str:
    text = data.decode("utf-8", errors="replace").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def _namespace_identity(entry: str) -> str | None:
    try:
        return os.readlink(Path("/proc/self/ns", entry))
    except OSError:
        return None


def _try_user_namespace(
    unshare_path: str,
    true_path: str,
    timeout_seconds: float = 3.0,
) -> dict[str, Any]:
    argv = [
        unshare_path,
        "--user",
        "--map-root-user",
        "--",
        true_path,
    ]
    try:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
            start_new_session=True,
        )
    except OSError as exc:
        return {
            "attempted": True,
            "returncode": None,
            "status": "failed",
            "stderr": f"{type(exc).__name__}: {exc}",
            "stdout": "",
        }

    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        cleanup_error = ""
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as exc:
            cleanup_error = f"; group cleanup failed: {type(exc).__name__}: {exc}"
            try:
                process.kill()
            except OSError as kill_exc:
                cleanup_error += (
                    f"; direct cleanup failed: {type(kill_exc).__name__}: {kill_exc}"
                )
        stdout, stderr = process.communicate()
        return {
            "attempted": True,
            "returncode": process.returncode,
            "status": "timeout",
            "stderr": _bounded_text(stderr) + cleanup_error,
            "stdout": _bounded_text(stdout),
        }

    return {
        "attempted": True,
        "returncode": process.returncode,
        "status": "success" if process.returncode == 0 else "failed",
        "stderr": _bounded_text(stderr),
        "stdout": _bounded_text(stdout),
    }


def build_report(try_userns: bool) -> dict[str, Any]:
    is_linux = platform.system() == "Linux"
    unshare_path = shutil.which("unshare")
    true_path = shutil.which("true")

    report: dict[str, Any] = {
        "commands": {
            "true": true_path,
            "unshare": unshare_path,
        },
        "kernel_settings": {
            name: _kernel_setting(path)
            for name, path in _KERNEL_SETTINGS.items()
        }
        if is_linux
        else {},
        "platform": {
            "is_linux": is_linux,
            "machine": platform.machine(),
            "python": platform.python_version(),
            "release": platform.release(),
            "system": platform.system(),
        },
        "proc_namespace_entries": {
            name: Path("/proc/self/ns", entry).exists()
            for name, entry in _NAMESPACE_ENTRIES.items()
        }
        if is_linux
        else {},
        "proc_namespace_ids": {
            name: _namespace_identity(entry)
            for name, entry in _NAMESPACE_ENTRIES.items()
        }
        if is_linux
        else {},
        "running_as_root": hasattr(os, "geteuid") and os.geteuid() == 0,
    }

    if not try_userns:
        test_result: dict[str, Any] = {
            "attempted": False,
            "returncode": None,
            "status": "not_requested",
            "stderr": "",
            "stdout": "",
        }
    elif not is_linux:
        test_result = {
            "attempted": False,
            "returncode": None,
            "status": "not_linux",
            "stderr": "",
            "stdout": "",
        }
    elif unshare_path is None or true_path is None:
        missing = [
            name
            for name, value in (("unshare", unshare_path), ("true", true_path))
            if value is None
        ]
        test_result = {
            "attempted": False,
            "returncode": None,
            "status": "command_missing",
            "stderr": "missing command: " + ", ".join(missing),
            "stdout": "",
        }
    else:
        test_result = _try_user_namespace(unshare_path, true_path)

    report["user_namespace_test"] = test_result
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report optional Linux namespace prerequisites for Minibox."
    )
    parser.add_argument(
        "--try-userns",
        action="store_true",
        help="attempt one short-lived unprivileged user namespace",
    )
    args = parser.parse_args()
    print(json.dumps(build_report(args.try_userns), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
