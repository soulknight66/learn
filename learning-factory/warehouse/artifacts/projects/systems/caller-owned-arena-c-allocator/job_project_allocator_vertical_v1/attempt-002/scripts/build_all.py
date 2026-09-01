from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "validation-output"
BIN = OUTPUT / "bin"
GCC = shutil.which("gcc")
FLAGS = [
    "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic", "-O2",
    "-fno-omit-frame-pointer", "-I", str(ROOT / "include"),
]
IMPLEMENTATIONS = {
    "reference": ROOT / "sealed/reference/allocator.c",
    "best-fit": ROOT / "sealed/alternatives/best_fit/allocator.c",
    "segregated-bins": ROOT / "sealed/alternatives/segregated_bins/allocator.c",
}


def command(argv: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
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
        check=check,
    )


def compile_binary(name: str, sources: list[Path], extra: list[str] | None = None) -> None:
    assert GCC is not None
    argv = [GCC, *FLAGS, *(extra or []), *map(str, sources), "-o", str(BIN / name)]
    result = command(argv, check=False)
    if result.returncode != 0:
        raise SystemExit(
            f"compile failed for {name}\nargv={argv!r}\nstdout={result.stdout}\nstderr={result.stderr}"
        )


def sanitizer_probe() -> tuple[bool, str]:
    assert GCC is not None
    probe_source = ROOT / "environment/sanitizer_probe.c"
    probe_binary = BIN / "sanitizer-probe"
    argv = [
        GCC, "-std=c11", "-fsanitize=address,undefined", str(probe_source),
        "-o", str(probe_binary),
    ]
    compiled = command(argv, check=False)
    if compiled.returncode != 0:
        return False, "compiler probe rejected address/undefined sanitizers"
    executed = command([str(probe_binary)], check=False)
    if executed.returncode != 0:
        return False, "sanitizer runtime probe did not execute successfully"
    return True, "compiler and runtime probe executed successfully"


def main() -> int:
    if GCC is None:
        raise SystemExit("gcc is required for this C challenge pack")
    BIN.mkdir(parents=True, exist_ok=True)
    version = command([GCC, "--version"]).stdout.splitlines()[0]
    for architecture, implementation in IMPLEMENTATIONS.items():
        compile_binary(f"{architecture}-public", [implementation, ROOT / "public_tests/contract.c"])
        compile_binary(
            f"{architecture}-withheld",
            [implementation, ROOT / "sealed/reference_tests/contract.c"],
        )
        compile_binary(
            f"{architecture}-model",
            [implementation, ROOT / "adversarial/model_randomized.c"],
        )
        compile_binary(
            f"{architecture}-benchmark",
            [implementation, ROOT / "benchmarks/benchmark.c"],
        )
    compile_binary(
        "segregated-integrity",
        [ROOT / "sealed/reference_tests/segregated_integrity.c"],
    )
    compile_binary(
        "debug-buggy",
        [ROOT / "debugging/coalesce-span/buggy/allocator.c",
         ROOT / "debugging/coalesce-span/regression.c"],
    )
    compile_binary(
        "debug-reference",
        [ROOT / "sealed/reference/allocator.c",
         ROOT / "debugging/coalesce-span/regression.c"],
    )
    compile_binary(
        "review-demonstration",
        [ROOT / "review_exercises/rounding-overflow/proposed/rounding.c",
         ROOT / "review_exercises/rounding-overflow/sealed/demonstrate.c"],
    )
    sanitizer_available, sanitizer_reason = sanitizer_probe()
    if sanitizer_available:
        for architecture, implementation in IMPLEMENTATIONS.items():
            compile_binary(
                f"{architecture}-model-sanitized",
                [implementation, ROOT / "adversarial/model_randomized.c"],
                ["-O1", "-fsanitize=address,undefined"],
            )
    report = {
        "schema_version": 1,
        "compiler": version,
        "compiler_path": GCC,
        "strict_flags": FLAGS,
        "platform": platform.platform(),
        "sanitizer": {
            "available": sanitizer_available,
            "probe": "compile and execute address+undefined sanitizer fixture",
            "reason": sanitizer_reason,
            "requested_architectures": list(IMPLEMENTATIONS),
        },
        "network_used": False,
        "binary_count": len(list(BIN.iterdir())),
    }
    (OUTPUT / "toolchain.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
