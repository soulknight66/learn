# Portable public tests

These tests exercise only deterministic C policy. They do not emulate reset,
CP15, MMIO, or ARM register preservation.

Run from the repository root:

```sh
make -C public_tests clean test
```

`KERNEL_SRC` defaults to `../starter` and may point to another candidate tree
with the same headers and source filenames. `CC` may be an absolute compiler
path. AddressSanitizer and UndefinedBehaviorSanitizer are enabled by default;
set `SANITIZERS=` only when the selected host compiler genuinely lacks them and
record that reduction in evidence.

The untouched starter is expected to report failed checks. Implement one
subsystem at a time and use the first reported contract failure as the next
small step. A public pass is not proof of target execution or hidden edge cases.
