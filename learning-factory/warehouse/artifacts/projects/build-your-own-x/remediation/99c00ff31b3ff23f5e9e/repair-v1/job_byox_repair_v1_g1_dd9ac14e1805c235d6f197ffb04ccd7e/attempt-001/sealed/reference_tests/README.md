# Sealed reference tests

`test_reference.py` extends the public suite with invalid CLI shapes, resource
limits, malformed bytes, declaration edge cases, skipped branches,
deterministic emission, runtime failures in native code, the execution budget,
and a fixed-seed corpus of generated expression trees.

Run from the repository root:

```bash
make -C sealed/reference clean all
MICA_BIN=sealed/reference/mica python3 sealed/reference_tests/test_reference.py
```

All scratch inputs, assembly, and executables are created beneath
`environment/.reference-test-work` and removed. The fixed seed makes failures
reproducible; no coverage or fuzzing label is asserted by this suite.
