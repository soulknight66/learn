from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(
    label: str,
    argv: list[str],
    *,
    pythonpath: str | None = None,
    expected: int = 0,
) -> None:
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if pythonpath is not None:
        environment["PYTHONPATH"] = pythonpath
    print(f"==> {label}", flush=True)
    completed = subprocess.run(argv, cwd=ROOT, env=environment, check=False)
    if completed.returncode != expected:
        raise SystemExit(
            f"{label} exited {completed.returncode}; expected {expected}"
        )


def main() -> int:
    reference = "sealed/reference"
    production = "production/implementation"
    run("syntax", [sys.executable, "environment/check_python.py"])
    for name, path in (("reference", reference), ("production candidate", production)):
        run(
            f"{name} public tests",
            [sys.executable, "-m", "unittest", "discover", "-s", "public_tests", "-v"],
            pythonpath=path,
        )
        run(
            f"{name} withheld tests",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "sealed/reference_tests",
                "-v",
            ],
            pythonpath=path,
        )
    run("student boundary", [sys.executable, "environment/check_boundary.py"])
    run(
        "crash fault",
        [sys.executable, "adversarial/fault-injection/crash_after_effect.py"],
        pythonpath=reference,
    )
    run(
        "concurrency stress",
        [sys.executable, "adversarial/stress/concurrent_workers.py"],
        pythonpath=reference,
    )
    run(
        "deterministic model fuzz",
        [
            sys.executable,
            "adversarial/fuzz/model_fuzz.py",
            "--seed",
            "20260830",
            "--steps",
            "160",
        ],
        pythonpath=reference,
    )
    run(
        "bug reproduction",
        [sys.executable, "debugging/dead-letter-off-by-one/regression.py"],
        pythonpath="debugging/dead-letter-off-by-one/buggy",
        expected=23,
    )
    run(
        "bug reference",
        [sys.executable, "debugging/dead-letter-off-by-one/regression.py"],
        pythonpath=reference,
    )
    run(
        "review reproducer",
        [
            sys.executable,
            "review_exercises/non_atomic_batch_claim/sealed/demonstrate.py",
        ],
        pythonpath="review_exercises/non_atomic_batch_claim/proposed:sealed/reference",
    )
    run(
        "bounded measured benchmark",
        [
            sys.executable,
            "benchmarks/benchmark.py",
            "--messages",
            "80",
            "--repetitions",
            "2",
            "--output",
            "benchmarks/results/smoke.json",
        ],
        pythonpath=reference,
    )
    print("all bounded event-service validation stages behaved as expected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
