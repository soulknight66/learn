# Public tests

These black-box tests cover only basic round-robin order, one-page VM permissions, and filesystem
round trips. Run:

```sh
make -C public_tests clean test
```

The unmodified starter compiles but fails all groups because it contains placeholders. Public tests
do not cover capacity exhaustion, sleeping, stale PIDs, overflow, cross-page atomicity, cleanup,
filesystem failure atomicity, or ARM execution. Do not encode special cases for these examples.
