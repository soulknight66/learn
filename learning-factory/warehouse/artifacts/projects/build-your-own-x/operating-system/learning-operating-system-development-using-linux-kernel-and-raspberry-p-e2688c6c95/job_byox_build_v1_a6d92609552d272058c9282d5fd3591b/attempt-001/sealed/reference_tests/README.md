# Sealed reference tests

These deterministic tests exercise the reference implementation's lifecycle edges, round-robin order, page boundaries, permission failures, copy-on-write isolation and capacity rollback, descriptor-copy semantics, filesystem rollback, cleanup, and corruption diagnostics.

Run from the repository root:

```sh
make -C sealed/reference_tests clean test
make -C sealed/reference_tests public
make -C sealed/reference_tests sanitize
```

The suite is reference evidence, not a learner-visible test oracle. It uses no network, clock, randomness, subprocesses from C, or machine-specific data.
