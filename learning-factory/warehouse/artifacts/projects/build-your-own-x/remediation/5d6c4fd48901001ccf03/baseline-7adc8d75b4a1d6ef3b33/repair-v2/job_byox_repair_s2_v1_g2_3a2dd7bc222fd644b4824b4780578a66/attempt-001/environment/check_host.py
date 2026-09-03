#!/usr/bin/env python3
"""Report namespace prerequisites without claiming integration correctness."""

import json
import os
import platform
import shutil
import subprocess


def main() -> int:
    unshare = shutil.which("unshare")
    report = {
        "linux": platform.system() == "Linux",
        "python": platform.python_version(),
        "unshare_path": unshare,
        "user_namespace_probe": "NOT_RUN",
    }
    if report["linux"] and unshare:
        try:
            completed = subprocess.run(
                [unshare, "--user", "--map-root-user", "--", "true"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5.0,
                check=False,
                start_new_session=True,
            )
        except subprocess.TimeoutExpired:
            report["user_namespace_probe"] = "TIMEOUT"
        else:
            report["user_namespace_probe"] = "AVAILABLE" if completed.returncode == 0 else "DENIED"
            report["probe_exit_code"] = completed.returncode
            if completed.stderr:
                report["probe_stderr"] = completed.stderr.decode("utf-8", errors="replace").strip()[:500]
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
