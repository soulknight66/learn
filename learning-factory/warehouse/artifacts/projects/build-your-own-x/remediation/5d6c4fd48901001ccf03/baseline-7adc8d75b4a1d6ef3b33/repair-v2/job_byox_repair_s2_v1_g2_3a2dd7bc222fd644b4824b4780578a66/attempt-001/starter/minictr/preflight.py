"""Setup-only child skeleton for an actionable unsupported-host check."""

from __future__ import annotations

import sys


def main() -> int:
    # TODO(stage 3): parse and validate bounded stdin exactly as the real child does, perform
    # namespace/rootfs setup without execing the workload, and report unsupported setup clearly.
    print("minictr preflight: setup check is not implemented", file=sys.stderr)
    return 69


if __name__ == "__main__":
    raise SystemExit(main())
