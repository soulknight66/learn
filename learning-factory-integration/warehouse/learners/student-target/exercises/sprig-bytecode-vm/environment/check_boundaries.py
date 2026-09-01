from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    visible = [Path("README.md"), Path("REQUIREMENTS.md"), Path("GRAMMAR.md"), Path("BYTECODE.md"), Path("CONCEPTS.md"), Path("DESIGN_QUESTIONS.md")]
    visible += sorted(Path("starter").rglob("*")) + sorted(Path("public_tests").rglob("*"))
    forbidden = ("sealed/", "EXPECTED_REVIEW", "root-cause.md", "patch.diff", "WithheldContractTests")
    leaks = []
    expected_starter = {
        Path("starter/README.md"),
        *(Path("starter/tinyvm") / name for name in (
            "__init__.py", "api.py", "compiler.py", "lexer.py", "model.py", "parser.py", "vm.py",
        )),
    }
    expected_public = {Path("public_tests/test_public.py")}
    actual_starter = {path for path in Path("starter").rglob("*") if path.is_file()}
    actual_public = {path for path in Path("public_tests").rglob("*") if path.is_file()}
    for path in sorted(expected_starter - actual_starter):
        leaks.append(f"missing learner-visible file: {path}")
    for path in sorted(actual_starter - expected_starter):
        leaks.append(f"unexpected learner-visible file: {path}")
    for path in sorted(expected_public - actual_public):
        leaks.append(f"missing public-test file: {path}")
    for path in sorted(actual_public - expected_public):
        leaks.append(f"unexpected public-test file: {path}")
    for path in visible:
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            for marker in forbidden:
                if marker in text:
                    leaks.append(f"{path}: leaked marker {marker!r}")
    starter = "\n".join(path.read_text(encoding="utf-8") for path in sorted(Path("starter/tinyvm").glob("*.py")))
    for stage in ("TODO(stage 1a)", "TODO(stage 1b)", "TODO(stage 2)", "TODO(stage 3)"):
        if stage not in starter:
            leaks.append(f"starter is missing progressive marker {stage}")
    if "NotImplementedError" not in starter:
        leaks.append("starter unexpectedly contains a completed implementation")
    if leaks:
        print("\n".join(leaks), file=sys.stderr)
        return 1
    print("learner-visible starter and public tests omit withheld paths and answer markers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
