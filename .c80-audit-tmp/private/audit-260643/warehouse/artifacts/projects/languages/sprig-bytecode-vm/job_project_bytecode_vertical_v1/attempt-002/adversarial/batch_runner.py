from __future__ import annotations

import json
import sys

import tinyvm


programs = json.load(sys.stdin)
results = []
for source in programs:
    result = tinyvm.run_source(source, max_steps=20_000)
    results.append({"outputs": result.outputs, "globals": result.globals})
json.dump({"engine": tinyvm.ENGINE, "results": results}, sys.stdout, sort_keys=True)
