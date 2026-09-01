from __future__ import annotations

import sys
from pathlib import Path

import tinyvm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "proposed"))
from optimizer import fold


source = "print false && (1 / 0);"
correct = tinyvm.run_source(source)
if correct.outputs != (0,): raise SystemExit("reference short-circuit baseline failed")
expression = tinyvm.parse_source(source).statements[0].expression
try:
    fold(expression)
except tinyvm.RuntimeFault as error:
    if "division by zero" not in str(error): raise
    print("proposed optimizer eagerly evaluates an unreachable RHS and changes valid-program behavior")
    raise SystemExit(0)
raise SystemExit("expected optimizer semantic regression did not reproduce")
