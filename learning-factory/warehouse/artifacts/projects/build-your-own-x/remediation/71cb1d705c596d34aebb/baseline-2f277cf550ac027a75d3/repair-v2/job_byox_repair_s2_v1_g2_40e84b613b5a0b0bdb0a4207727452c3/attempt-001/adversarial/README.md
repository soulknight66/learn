# Harness-only adversarial checks

This directory is outside the learner view. `test_boundaries.py` sends bounded,
deterministic edge cases to a selected binary. It is a regression suite, not a
coverage-guided fuzzer and not evidence for a `FUZZED` label.

```sh
MSH_BIN="$PWD/sealed/reference/msh" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  adversarial/test_boundaries.py
```

The cases include both exact 1 MiB line forms (EOF and LF-delimited) and a
strictly over-limit line. A harness self-test forks a same-group descendant and
checks that deadline cleanup removes it. Targets use the shared bounded
process-group runner.
