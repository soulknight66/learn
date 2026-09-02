"""Namespace child helper skeleton.

This module must be imported before changing root. Keep setup order explicit and directly exec the
validated argv; never route workload data through a shell.
"""

from __future__ import annotations

import sys


def main() -> int:
    # TODO(stage 3): read at most 1 MiB of spec JSON from stdin and validate it again.
    # TODO(stage 3): make mount propagation private, bind/remount rootfs, mount proc inside it,
    # set the UTS hostname, chroot, chdir, construct a minimal environment, then os.execvpe argv.
    print("minictr child: setup is not implemented", file=sys.stderr)
    return 125


if __name__ == "__main__":
    raise SystemExit(main())
