# Harness-only adversarial checks

This directory is outside the learner view. `test_boundaries.py` sends bounded,
deterministic edge cases to a selected binary. It is a regression suite, not a
coverage-guided fuzzer and not evidence for a `FUZZED` label.

```sh
MSH_BIN="$PWD/sealed/reference/msh" \
  python3 adversarial/test_boundaries.py
```
