# Sealed reference tests

This suite is validator-only.  `test_private.py` exercises compilation and CLI
behavior through subprocess argument arrays.  `test_vm.c` directly supplies
malformed bytecode to the VM API, covering checks the source compiler cannot
naturally produce.  `test_verify_pack.py` copies only allowlisted pack roots to
bounded local scratch space and confirms that unexpected top-level files and
symlinks are rejected.

From the repository root:

```sh
sealed/reference_tests/run.sh
```

The runner builds both targets with strict C17 warnings, runs the native VM
tests, then runs the Python black-box tests.  Direct VM cases assert the full
source-location prefix for runtime failures.  Black-box cases cover each
checked arithmetic class, zero-budget semantics, and both sides of the syntax
depth boundary; therefore the same checks run in the documented sanitizer
rerun.  Each subprocess has a bounded timeout, including five seconds for the
tower and depth cases.
