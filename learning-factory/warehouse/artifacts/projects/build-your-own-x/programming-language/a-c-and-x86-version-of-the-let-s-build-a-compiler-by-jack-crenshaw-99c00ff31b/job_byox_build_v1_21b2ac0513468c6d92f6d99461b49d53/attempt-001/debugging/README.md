# Debugging exercise

## Exercise 01: the divide that crashes

A learner backend handles ordinary signed division correctly but the native
program traps for one valid Mica input. Assume the divisor-zero check already
works.

Inspect this plausible lowering sequence:

```asm
# dividend is in %rax; divisor is in %rcx
cqto
idivq %rcx
```

Reproduce the problem with values expressible under `REQUIREMENTS.md`, explain
why the interpreter may not show the same host failure, and propose a lowering
that preserves both quotient and remainder semantics. Also name the exact check
that must occur before `idivq`.

The answer and corrected reference fragment are isolated in the corresponding
sealed exercise directory.
