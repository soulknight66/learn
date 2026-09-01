# Public tests

These deterministic standard-library tests document representative behavior. Their numeric prefixes
match the suggested implementation order.

```bash
PYTHONPATH=starter python3 -m unittest public_tests.test_01_reader -v
PYTHONPATH=starter python3 -m unittest public_tests.test_02_evaluator -v
PYTHONPATH=starter python3 -m unittest public_tests.test_03_functions -v
PYTHONPATH=starter python3 -m unittest public_tests.test_04_compiler_vm -v
PYTHONPATH=starter python3 -m unittest public_tests.test_05_cli -v
```

The full command is in the root README. Passing these cases is necessary but not sufficient; design
for the complete contract, including malformed input and boundaries. Tests import `sprig` from
`PYTHONPATH`, so the same suite can exercise another conforming package without modification.
