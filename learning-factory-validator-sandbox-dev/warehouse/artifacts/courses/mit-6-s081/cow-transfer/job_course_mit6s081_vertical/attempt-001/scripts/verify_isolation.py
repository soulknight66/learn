from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    view = Path("student_safe")
    forbidden = {"sealed", "examiner_only", "hidden_tests", "rubric.md", "reference"}
    errors: list[str] = []
    for path in [view, *view.rglob("*")]:
        if path.is_symlink():
            errors.append(f"symlink in student view: {path}")
        if path.name.casefold() in forbidden:
            errors.append(f"forbidden name in student view: {path}")
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace").casefold()
        for path in view.rglob("*")
        if path.is_file()
    )
    for marker in ("examiner_only/", "hidden_tests/", "rubric.md"):
        if marker in text:
            errors.append(f"student material leaks examiner path marker: {marker}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("student tree contains no examiner paths, sealed material, or symlinks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
