# Learner and agent contract

Implement the challenge only in `starter/`. Treat headers in
`starter/include/kernel/` and the observable requirements as stable interfaces.

## Safety and determinism

- Keep the kernel freestanding: no libc calls, heap allocation, host syscalls,
  shell-built generated source, or network access.
- Use fixed-size tables and explicit error returns. Never depend on uninitialized
  memory, wall-clock time, random ordering, or pointer values in output.
- Preserve the five scheduler states and validate every state transition.
- Check alignment, range, overflow, permissions, and duplicate mappings before
  mutating VM state.
- Make filesystem mutations failure-atomic: an error leaves metadata and bytes
  unchanged.
- Do not edit public assertions merely to obtain a pass.

## Recommended loop

```sh
make -C public_tests clean test
make -C starter clean all CROSS_COMPILE=/absolute/path/to/arm-none-eabi-
```

Use argv-based, bounded QEMU invocations. If a process hangs, retain the serial
log and explain the last stable marker. Do not claim hardware behavior from host
tests alone.

## Scope boundaries

The initial learner-facing pack is exactly the selection in
`environment/student_view_policy.json`, including `LICENSE_BOUNDARY.md`. After
an attempt, only the extra files selected by
`environment/post_attempt_view_policy.json` may be disclosed. A publisher must
use one explicit policy and pass the strict stage-specific audit described in
`environment/README.md`; source layout alone is not publication evidence. Do
not seek evaluator-only material. Do not copy from the provenance link: its
license is not asserted for this project.
