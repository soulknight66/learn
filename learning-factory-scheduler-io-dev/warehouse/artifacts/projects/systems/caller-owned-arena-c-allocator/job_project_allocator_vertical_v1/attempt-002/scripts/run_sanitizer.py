from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "validation-output/toolchain.json"
RESULT = ROOT / "validation-output/sanitizer-result.json"
ARCHITECTURES = ["reference", "best-fit", "segregated-bins"]


def main() -> int:
    toolchain = json.loads(REPORT.read_text(encoding="utf-8"))
    available = bool(toolchain["sanitizer"]["available"])
    result: dict[str, object] = {
        "schema_version": 1,
        "probe_available": available,
        "probe_reason": toolchain["sanitizer"]["reason"],
        "requested_architectures": ARCHITECTURES,
        "architectures": {},
    }
    if not available:
        result["status"] = "SKIPPED_UNAVAILABLE"
        result["exit_code"] = None
    else:
        architecture_results: dict[str, object] = {}
        for architecture in ARCHITECTURES:
            completed = subprocess.run(
                [str(ROOT / "validation-output/bin" /
                     f"{architecture}-model-sanitized")],
                cwd=ROOT,
                env={
                    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                    "LANG": "C.UTF-8",
                    "LC_ALL": "C.UTF-8",
                    "ASAN_OPTIONS": "detect_leaks=0:abort_on_error=1",
                    "UBSAN_OPTIONS": "halt_on_error=1",
                },
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
            architecture_results[architecture] = {
                "exit_code": completed.returncode,
                "stdout": completed.stdout[-2000:],
                "stderr": completed.stderr[-2000:],
            }
        passed = all(
            details["exit_code"] == 0
            for details in architecture_results.values()
            if isinstance(details, dict)
        )
        result.update(
            status="PASS" if passed else "FAIL",
            exit_code=0 if passed else 1,
            architectures=architecture_results,
        )
    RESULT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in {"PASS", "SKIPPED_UNAVAILABLE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
