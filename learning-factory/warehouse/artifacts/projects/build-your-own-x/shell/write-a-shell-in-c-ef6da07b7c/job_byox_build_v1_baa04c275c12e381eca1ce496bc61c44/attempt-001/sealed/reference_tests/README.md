# Sealed reference tests

These evaluator-only tests combine white-box parser/job-table checks with black-box process, status, process-group, and pseudo-terminal checks.

From the repository root:

```sh
make -C sealed/reference clean all
make -C sealed/reference_tests clean test
python3 sealed/reference_tests/audit_pack.py
```

`make test` expects `../reference/msh-reference` to exist. The pseudo-terminal test has bounded reads and cleans up its child on failure. Test binaries and object-like scratch artifacts can be removed with `make -C sealed/reference_tests clean` after recording results.

Passing here is local evidence only. The factory must rerun validation in an independently controlled harness before changing labels.
