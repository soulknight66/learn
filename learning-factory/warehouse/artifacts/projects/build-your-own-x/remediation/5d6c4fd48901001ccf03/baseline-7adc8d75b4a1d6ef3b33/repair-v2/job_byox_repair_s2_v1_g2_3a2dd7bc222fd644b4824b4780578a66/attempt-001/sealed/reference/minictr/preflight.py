"""Setup-only namespace helper used to reject unsupported hosts before workload launch."""

from __future__ import annotations

import json
import sys

from .child import MAX_PAYLOAD, _prepare_root
from .spec import ContainerSpec

EX_UNAVAILABLE = 69
EX_DATAERR = 65


def main() -> int:
    payload = sys.stdin.buffer.read(MAX_PAYLOAD + 1)
    if len(payload) > MAX_PAYLOAD:
        print("minictr preflight: invalid spec: payload exceeds 1 MiB", file=sys.stderr)
        return EX_DATAERR
    try:
        value = json.loads(payload.decode("utf-8"))
        spec = ContainerSpec.from_mapping(value)
    except Exception as exc:
        print(f"minictr preflight: invalid spec: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EX_DATAERR
    try:
        _prepare_root(spec)
    except Exception as exc:
        mode = "read-only root" if spec.readonly_root else "writable root"
        print(
            f"minictr preflight: UNSUPPORTED {mode} setup: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        if spec.readonly_root:
            print(
                "minictr preflight: the workload was not started; use a compatible local "
                "filesystem/host, or explicitly choose readonly_root=false only for a disposable rootfs",
                file=sys.stderr,
            )
        return EX_UNAVAILABLE
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
