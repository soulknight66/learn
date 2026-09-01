"""Non-mutating capability probe for rootless user namespaces."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys


def main() -> int:
    executable = shutil.which("unshare")
    result: dict[str, object] = {
        "linux": sys.platform.startswith("linux"),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "unshare": executable,
    }
    if not result["linux"] or executable is None:
        result.update({"supported": False, "reason": "Linux or util-linux unshare unavailable"})
        print(json.dumps(result, sort_keys=True))
        return 1

    try:
        completed = subprocess.run(
            [executable, "--user", "--map-root-user", "--", "true"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5.0,
            check=False,
            start_new_session=True,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        result.update({"supported": False, "reason": type(exc).__name__})
        print(json.dumps(result, sort_keys=True))
        return 1

    result.update(
        {
            "returncode": completed.returncode,
            "stderr": completed.stderr.decode("utf-8", "replace").strip(),
            "supported": completed.returncode == 0,
        }
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if completed.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
