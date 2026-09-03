# Learner-agent contract

Work only in the learner-visible files and `starter/`. Treat `public_tests/` as
read-only test material. Do not inspect, copy, or infer content from any sealed
area; independent evaluation assumes the implementation was derived from the
published requirements.

## Implementation rules

- Keep the declarations, constants, enum values, and public structure layout
  in `starter/include/minios.h` unchanged.
- Replace all TODO stubs in the three `starter/src/*.c` files.
- Use fixed-capacity storage only. Do not call allocation, file, process,
  timing, randomness, or networking APIs from the host.
- Validate pointers before dereferencing them and use comparisons that cannot
  wrap when checking address or buffer bounds.
- A rejected mutating operation must not partially change observable state.
- Keep the code valid freestanding C11: loops that copy or clear bytes are
  acceptable; hosted-library shortcuts are not.
- Do not weaken compiler flags or modify tests to make a failure disappear.

## Checks

Run from the repository root:

```bash
make -C starter clean compile
make -C starter test
```

Before considering the task complete, explain the invariants you rely on,
review every state transition, and test the exact-capacity and one-past-limit
cases. A prose claim of success is not evidence; captured test results are.
