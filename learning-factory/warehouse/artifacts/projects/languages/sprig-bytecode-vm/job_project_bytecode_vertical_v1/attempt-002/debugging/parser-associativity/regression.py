from __future__ import annotations

import sys

import tinyvm


result = tinyvm.run_source("print 20 - 5 - 3;")
if result.outputs != (12,):
    print(f"subtraction grouped incorrectly: wanted 12, observed {result.outputs}", file=sys.stderr)
    raise SystemExit(1)
print("subtraction is left-associative: (20 - 5) - 3 == 12")
