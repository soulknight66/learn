# Public host tests

These tests exercise the platform-neutral contracts for terminal initialization/output, basic
Set-1 state, and queue capacity/FIFO behavior. They intentionally do not cover every scan code,
malformed sequence, control-character edge, memory-ordering concern, IRQ/PIC operation, or ELF
layout.

From the repository root:

```sh
make -C public_tests PROJECT=../starter run
```

The unmodified starter is expected to compile and report failures. Treat a pass as feedback, not as
independent completion evidence.
