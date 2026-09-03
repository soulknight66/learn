"""Namespace child helper. Imported before chroot, then directly execs the workload."""

from __future__ import annotations

import ctypes
import json
import os
import sys

from .paths import validate_rootfs
from .spec import ContainerSpec

MAX_PAYLOAD = 1024 * 1024
MS_RDONLY = 1
MS_NOSUID = 2
MS_NODEV = 4
MS_NOEXEC = 8
MS_REMOUNT = 32
MS_BIND = 4096
MS_REC = 16384
MS_PRIVATE = 1 << 18


def _as_bytes(value: str | None):
    return None if value is None else os.fsencode(value)


def _mount(source: str | None, target: str, flags: int, filesystem: str | None = None) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    result = libc.mount(
        _as_bytes(source), _as_bytes(target), _as_bytes(filesystem), ctypes.c_ulong(flags), None
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), target)


def _set_hostname(hostname: str) -> None:
    encoded = hostname.encode("ascii")
    libc = ctypes.CDLL(None, use_errno=True)
    result = libc.sethostname(encoded, len(encoded))
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def _prepare_root(spec: ContainerSpec) -> None:
    root = validate_rootfs(spec.rootfs)
    proc = root / "proc"
    if proc.is_symlink() or not proc.is_dir():
        raise ValueError("rootfs must contain a real proc directory")
    _mount(None, "/", MS_REC | MS_PRIVATE)
    _mount(str(root), str(root), MS_BIND | MS_REC)
    if spec.readonly_root:
        _mount(None, str(root), MS_BIND | MS_REMOUNT | MS_RDONLY)
    _mount("proc", str(proc), MS_NOSUID | MS_NODEV | MS_NOEXEC, "proc")
    _set_hostname(spec.hostname)
    os.chroot(root)
    os.chdir("/")


def main() -> int:
    payload = sys.stdin.buffer.read(MAX_PAYLOAD + 1)
    if len(payload) > MAX_PAYLOAD:
        print("minictr child: spec exceeds 1 MiB", file=sys.stderr)
        return 125
    try:
        value = json.loads(payload.decode("utf-8"))
        spec = ContainerSpec.from_mapping(value)
        _prepare_root(spec)
        environment = {"HOME": "/", "LANG": "C", "PATH": "/usr/bin:/bin"}
        environment.update(spec.env)
        os.execvpe(spec.command[0], list(spec.command), environment)
    except Exception as exc:
        print(f"minictr child: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 126
    return 126


if __name__ == "__main__":
    raise SystemExit(main())
