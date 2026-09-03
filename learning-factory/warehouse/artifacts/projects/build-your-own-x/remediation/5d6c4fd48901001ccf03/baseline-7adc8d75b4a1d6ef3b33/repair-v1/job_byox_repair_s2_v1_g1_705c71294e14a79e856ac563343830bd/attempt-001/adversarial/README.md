# Adversarial evaluator material

This directory is not part of the learner view. Its tests exercise common bypass attempts against
the sealed reference: sibling-prefix paths, symlink escapes, shell metacharacters in workload
arguments, SQL-looking identifiers at lookup time, and oversized setup payloads. They remain unit
tests and do not establish kernel containment.

```bash
PYTHON311="${PYTHON311:-/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3}"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  "$PYTHON311" -m unittest discover -s adversarial -v
```
