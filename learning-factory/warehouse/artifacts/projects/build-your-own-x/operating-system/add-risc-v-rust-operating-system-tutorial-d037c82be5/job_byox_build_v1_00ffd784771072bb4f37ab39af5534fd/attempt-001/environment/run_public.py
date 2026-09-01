"""Run the learner-visible Rust tests offline with a bounded subprocess."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "public_tests" / "Cargo.toml"


def main() -> int:
    cargo = shutil.which("cargo")
    if cargo is None:
        print("PUBLIC_TESTS: BLOCKED (cargo not found on PATH)")
        return 2

    argv = [cargo, "test", "--offline", "--manifest-path", str(MANIFEST)]
    environment = os.environ.copy()
    environment["CARGO_NET_OFFLINE"] = "true"
    print("PUBLIC_TESTS_ARGV:", repr(argv))
    try:
        completed = subprocess.run(
            argv,
            cwd=ROOT,
            env=environment,
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        print("PUBLIC_TESTS: TIMEOUT (120 seconds)")
        return 124
    print(f"PUBLIC_TESTS_EXIT: {completed.returncode}")
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
