# Sealed reference tests

The focused suite covers capacity, error precedence, failure atomicity, independent descriptor
cursors, process-slot reuse, cross-subsystem cleanup, and deliberately corrupted public state. The
adversarial driver applies 25,000 deterministic mixed operations and calls the invariant checker
after each one.

```sh
make -C sealed/reference_tests clean run
make -C sealed/reference_tests sanitized
```

The sanitizer target uses AddressSanitizer and UndefinedBehaviorSanitizer. Leak detection is disabled
because this sandbox blocks the process inspection LeakSanitizer requires; CairnOS performs no dynamic
allocation in any case.

`make -C sealed/reference_tests benchmark` is an opt-in timing probe, not a stable performance test.
No benchmark label or production claim follows from running it.
