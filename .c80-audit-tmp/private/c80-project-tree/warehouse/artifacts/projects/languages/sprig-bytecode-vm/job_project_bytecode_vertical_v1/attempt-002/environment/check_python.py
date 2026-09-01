from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    failures = []
    for path in sorted(Path(".").rglob("*.py")):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (OSError, SyntaxError, UnicodeError) as error:
            failures.append(f"{path}: {error}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"compiled {len(list(Path('.').rglob('*.py')))} Python sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
