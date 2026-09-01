"""Small setup process entered through the namespace launcher."""

from __future__ import annotations

import ctypes
import json
import os
import re
import stat
import sys
from pathlib import PurePosixPath
from typing import Any

_PAYLOAD_KEYS = frozenset(
    {"schema_version", "rootfs", "argv", "env", "hostname", "executable"}
)
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z", re.ASCII)
_HOSTNAME = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z", re.ASCII
)
_MAX_PAYLOAD_BYTES = 1_048_576
_MAX_STATUS_BYTES = 2048

MS_NOSUID = 2
MS_NODEV = 4
MS_NOEXEC = 8
MS_REC = 16_384
MS_PRIVATE = 1 << 18
PR_SET_NO_NEW_PRIVS = 38

_LIBC = ctypes.CDLL(None, use_errno=True)
_LIBC.mount.argtypes = [
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_ulong,
    ctypes.c_char_p,
]
_LIBC.mount.restype = ctypes.c_int
_LIBC.sethostname.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
_LIBC.sethostname.restype = ctypes.c_int
_LIBC.prctl.argtypes = [
    ctypes.c_int,
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_ulong,
]
_LIBC.prctl.restype = ctypes.c_int


def _bytes(value: str | None) -> bytes | None:
    return None if value is None else value.encode("utf-8")


def _syscall_error(operation: str) -> OSError:
    error_number = ctypes.get_errno()
    return OSError(error_number, f"{operation}: {os.strerror(error_number)}")


def _mount(
    source: str | None,
    target: str,
    filesystem: str | None,
    flags: int,
    data: str | None = None,
) -> None:
    if _LIBC.mount(
        _bytes(source), _bytes(target), _bytes(filesystem), flags, _bytes(data)
    ) != 0:
        raise _syscall_error(f"mount {target}")


def _set_hostname(hostname: str) -> None:
    encoded = hostname.encode("ascii")
    if _LIBC.sethostname(encoded, len(encoded)) != 0:
        raise _syscall_error("sethostname")


def _no_new_privileges() -> None:
    if _LIBC.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        raise _syscall_error("prctl(PR_SET_NO_NEW_PRIVS)")


def _payload() -> dict[str, Any]:
    raw = sys.stdin.buffer.read(_MAX_PAYLOAD_BYTES + 1)
    if len(raw) > _MAX_PAYLOAD_BYTES:
        raise ValueError("launcher payload is too large")
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant {value!r}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    decoded = json.loads(
        raw.decode("utf-8"),
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicate_keys,
    )
    if not isinstance(decoded, dict) or frozenset(decoded) != _PAYLOAD_KEYS:
        raise ValueError("launcher payload has an invalid shape")
    if (
        isinstance(decoded["schema_version"], bool)
        or not isinstance(decoded["schema_version"], int)
        or decoded["schema_version"] != 1
    ):
        raise ValueError("launcher payload has an invalid version")
    for name in ("rootfs", "hostname", "executable"):
        if not isinstance(decoded[name], str) or "\x00" in decoded[name]:
            raise ValueError(f"launcher field {name} is invalid")
    if not os.path.isabs(decoded["rootfs"]) or not os.path.isabs(decoded["executable"]):
        raise ValueError("launcher paths must be absolute")
    if ".." in PurePosixPath(decoded["executable"]).parts:
        raise ValueError("launcher executable must not contain traversal")
    if _HOSTNAME.fullmatch(decoded["hostname"]) is None:
        raise ValueError("launcher hostname is invalid")
    argv = decoded["argv"]
    if (
        not isinstance(argv, list)
        or not argv
        or any(
            not isinstance(value, str) or not value or "\x00" in value
            for value in argv
        )
    ):
        raise ValueError("launcher argv is invalid")
    environment = decoded["env"]
    if not isinstance(environment, dict):
        raise ValueError("launcher environment is invalid")
    for name, value in environment.items():
        if (
            not isinstance(name, str)
            or _ENV_NAME.fullmatch(name) is None
            or not isinstance(value, str)
            or "\x00" in value
        ):
            raise ValueError("launcher environment is invalid")
    return decoded


def _status_descriptor() -> int:
    raw = os.environ.get("MINIBOX_STATUS_FD")
    if raw is None or not raw.isascii() or not raw.isdecimal():
        raise ValueError("launcher did not provide a status descriptor")
    descriptor = int(raw, 10)
    if descriptor < 3:
        raise ValueError("launcher status descriptor is invalid")
    if not stat.S_ISFIFO(os.fstat(descriptor).st_mode):
        raise ValueError("launcher status descriptor is not a pipe")
    os.set_inheritable(descriptor, False)
    return descriptor


def _write_status(descriptor: int, message: bytes) -> None:
    bounded = message[:_MAX_STATUS_BYTES]
    view = memoryview(bounded)
    while view:
        written = os.write(descriptor, view)
        if written == 0:
            raise OSError("short write to launcher status pipe")
        view = view[written:]


def _prepare_root(payload: dict[str, Any]) -> None:
    _mount(None, "/", None, MS_REC | MS_PRIVATE)
    _set_hostname(payload["hostname"])
    try:
        os.setgroups([])
    except PermissionError:
        # util-linux may have already disabled setgroups for the uid mapping.
        pass
    os.setgid(0)
    os.setuid(0)
    os.chroot(payload["rootfs"])
    os.chdir("/")
    proc_metadata = os.lstat("/proc")
    if stat.S_ISLNK(proc_metadata.st_mode) or not stat.S_ISDIR(proc_metadata.st_mode):
        raise OSError("rootfs /proc must be a real directory")
    _mount("proc", "/proc", "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC)
    _no_new_privileges()
    os.umask(0o077)


def main() -> int:
    status_descriptor: int | None = None
    try:
        status_descriptor = _status_descriptor()
        payload = _payload()
        _prepare_root(payload)
        environment = {"PATH": "/bin:/usr/bin"}
        environment.update(payload["env"])
        _write_status(status_descriptor, b"READY\n")
        os.execve(payload["executable"], payload["argv"], environment)
    except Exception as exc:
        message = f"minibox child setup failed: {type(exc).__name__}: {exc}\n"
        if status_descriptor is not None:
            try:
                _write_status(status_descriptor, ("ERROR " + message).encode("utf-8"))
            except OSError:
                pass
        sys.stderr.write(message)
        return 125
    return 125


if __name__ == "__main__":
    raise SystemExit(main())
