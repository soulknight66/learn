from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
STAGES: list[tuple[str, list[str], dict[str, str], int]] = [
    ("syntax", [PYTHON, "environment/check_python.py"], {}, 0),
    (
        "reference public tests",
        [PYTHON, "-m", "unittest", "discover", "-s", "public_tests", "-v"],
        {"PYTHONPATH": str(ROOT / "sealed/reference")},
        0,
    ),
    (
        "reference recovery tests",
        [PYTHON, "-m", "unittest", "discover", "-s", "sealed/reference_tests", "-v"],
        {"PYTHONPATH": str(ROOT / "sealed/reference")},
        0,
    ),
    (
        "instrumented public tests",
        [PYTHON, "-m", "unittest", "discover", "-s", "public_tests", "-v"],
        {"PYTHONPATH": str(ROOT / "production/implementation")},
        0,
    ),
    (
        "instrumented recovery tests",
        [PYTHON, "-m", "unittest", "discover", "-s", "sealed/reference_tests", "-v"],
        {"PYTHONPATH": str(ROOT / "production/implementation")},
        0,
    ),
    (
        "reference model fuzz",
        [PYTHON, "adversarial/fuzz/model_fuzz.py", "--operations", "600"],
        {"KVSTORE_IMPL": "reference"},
        0,
    ),
    (
        "instrumented model fuzz",
        [PYTHON, "adversarial/fuzz/model_fuzz.py", "--operations", "600"],
        {"KVSTORE_IMPL": "production"},
        0,
    ),
    (
        "instrumented thread stress",
        [PYTHON, "adversarial/stress/thread_stress.py", "--threads", "6", "--operations", "80"],
        {"KVSTORE_IMPL": "production"},
        0,
    ),
    (
        "instrumented torn-tail fault",
        [PYTHON, "adversarial/fault-injection/torn_tail.py"],
        {"KVSTORE_IMPL": "production"},
        0,
    ),
    (
        "debugging defect reproduction",
        [PYTHON, "debugging/lost-delete/test_bug.py"],
        {"KVSTORE_IMPL": "buggy"},
        1,
    ),
    (
        "debugging reference regression",
        [PYTHON, "debugging/lost-delete/test_bug.py"],
        {"KVSTORE_IMPL": "reference"},
        0,
    ),
    (
        "measured smoke benchmark",
        [
            PYTHON,
            "benchmarks/benchmark.py",
            "--operations",
            "500",
            "--output",
            "benchmarks/results/smoke.json",
        ],
        {},
        0,
    ),
]


def main() -> int:
    for name, command, additions, expected_exit in STAGES:
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment.update(additions)
        print(f"==> {name}", flush=True)
        completed = subprocess.run(command, cwd=ROOT, env=environment, check=False)
        if completed.returncode != expected_exit:
            print(
                f"{name}: expected exit {expected_exit}, got {completed.returncode}",
                file=sys.stderr,
            )
            return 1
    print("all bounded validation stages behaved as expected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
