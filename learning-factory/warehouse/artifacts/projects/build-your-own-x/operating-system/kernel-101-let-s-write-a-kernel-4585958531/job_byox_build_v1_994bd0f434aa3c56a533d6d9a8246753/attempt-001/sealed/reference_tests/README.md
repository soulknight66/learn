# Sealed reference tests

These deterministic tests cover boundary and failure-atomicity cases omitted from the learner-facing
suite. They compile the sealed reference by default:

```sh
make -C sealed/reference_tests test
make -C sealed/reference_tests sanitize
```

The sanitizer target is supplementary and may be unavailable on some C toolchains. No test in
this directory promotes validation status; the external harness remains authoritative.
