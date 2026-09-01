# Adversarial checks (evaluator-only)

This directory is not part of the learner view. Its deterministic cases target archive-prefix confusion, late malicious metadata, symlink replacement, and special-file handling.

Run against the sealed reference with:

```bash
PYTHONPATH=sealed/reference python3.11 -m unittest discover -s adversarial -v
```

These are example attack cases, not fuzzing evidence or a complete security assessment.
