from __future__ import annotations

import tinyvm


try:
    tinyvm.run_source("print 1;")
except NotImplementedError:
    print("starter is importable and intentionally incomplete")
    raise SystemExit(0)
raise SystemExit("starter must not contain the sealed implementation")
