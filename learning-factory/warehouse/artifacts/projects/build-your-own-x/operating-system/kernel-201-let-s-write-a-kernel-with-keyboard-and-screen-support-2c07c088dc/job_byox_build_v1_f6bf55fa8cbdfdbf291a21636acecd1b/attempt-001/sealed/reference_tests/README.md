# Sealed reference tests

These host tests are solution-bearing because they expose boundary expectations beyond the public
suite. They compile the pure terminal and keyboard modules with warnings as errors. The normal test
does not execute privileged instructions and therefore cannot validate port I/O, IDT loading, PIC
behavior, or emulator boot.

```sh
make -C sealed/reference_tests run
make -C sealed/reference_tests sanitize
```

The sanitizer target is supplementary and depends on host runtime support.
