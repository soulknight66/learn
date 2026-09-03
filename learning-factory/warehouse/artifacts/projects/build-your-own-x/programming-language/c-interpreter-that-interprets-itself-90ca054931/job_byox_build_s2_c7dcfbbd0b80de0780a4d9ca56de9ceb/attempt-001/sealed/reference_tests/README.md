# Sealed reference tests

This suite is validator-only.  `test_private.py` exercises compilation and CLI
behavior through subprocess argument arrays.  `test_vm.c` directly supplies
malformed bytecode to the VM API, covering checks the source compiler cannot
naturally produce.

From the repository root:

```sh
sealed/reference_tests/run.sh
```

The runner builds both targets with strict C17 warnings, runs the native VM
tests, then runs the Python black-box tests.  The tower test has a bounded
five-second subprocess timeout.
