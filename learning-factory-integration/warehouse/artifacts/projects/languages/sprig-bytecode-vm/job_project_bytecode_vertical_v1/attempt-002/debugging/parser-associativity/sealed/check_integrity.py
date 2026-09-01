from __future__ import annotations

from pathlib import Path


buggy = Path("debugging/parser-associativity/buggy/tinyvm/parser.py").read_text(encoding="utf-8")
fixed = Path("debugging/parser-associativity/sealed/fixed/tinyvm/parser.py").read_text(encoding="utf-8")
expected_bug = "right = self._term()"
expected_fix = "right = self._factor()"
if buggy.count(expected_bug) != 1 or fixed.count(expected_fix) != 1:
    raise SystemExit("challenge no longer contains the isolated parser mutation")
normalized = buggy.replace(expected_bug, expected_fix)
if normalized != fixed:
    raise SystemExit("buggy and fixed parser differ by more than the isolated root cause")
patch = Path("debugging/parser-associativity/sealed/patch.diff").read_text(encoding="utf-8")
if "-                right = self._term()" not in patch or "+                right = self._factor()" not in patch:
    raise SystemExit("sealed patch does not describe the proven repair")
print("isolated mutation and repair patch are structurally consistent")
