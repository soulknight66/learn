from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHARED = "sealed/shared"


def run(label: str, argv: list[str], *, path: str | None = None, expected: int = 0) -> None:
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if path is not None:
        environment["PYTHONPATH"] = path
    print(f"==> {label}", flush=True)
    completed = subprocess.run(argv, cwd=ROOT, env=environment, check=False)
    if completed.returncode != expected:
        raise SystemExit(
            f"{label} exited {completed.returncode}; expected {expected}"
        )


def main() -> int:
    implementations = {
        "reference": f"sealed/reference:{SHARED}",
        "thread-per-connection": f"sealed/alternatives/thread_per_connection:{SHARED}",
        "event-loop": f"sealed/alternatives/event_loop:{SHARED}",
    }
    run("syntax", [sys.executable, "environment/check_python.py"])
    for name, path in implementations.items():
        run(f"{name} public contract", [sys.executable, "-m", "unittest", "discover", "-s", "public_tests", "-v"], path=path)
        run(f"{name} hidden contract", [sys.executable, "-m", "unittest", "discover", "-s", "sealed/reference_tests", "-v"], path=path)
    run("parser adversary", [sys.executable, "adversarial/parser/check.py", "--iterations", "120"], path=implementations["reference"])
    run("fault containment", [sys.executable, "adversarial/fault-injection/check.py"], path=implementations["reference"])
    run("slow-client recovery", [sys.executable, "adversarial/slow-client/check.py"], path=implementations["reference"])
    run("bug reproduction", [sys.executable, "debugging/partial-body/regression.py"], path="debugging/partial-body/buggy", expected=1)
    run("debug reference", [sys.executable, "debugging/partial-body/regression.py"], path=SHARED)
    run("review finding reproduction", [sys.executable, "review_exercises/cache-layer/sealed/demonstrate.py"], path=f"review_exercises/cache-layer/proposed:{SHARED}")
    run(
        "bounded benchmark",
        [sys.executable, "benchmarks/benchmark.py", "--requests", "40", "--concurrency", "4", "--output", "benchmarks/results/smoke.json"],
    )
    print("all bounded validation stages behaved as expected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
