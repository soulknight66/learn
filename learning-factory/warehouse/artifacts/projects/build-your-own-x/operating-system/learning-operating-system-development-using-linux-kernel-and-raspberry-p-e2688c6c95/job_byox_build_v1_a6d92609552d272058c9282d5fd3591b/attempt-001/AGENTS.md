# Contributor instructions

Work only in `starter/` unless a task explicitly asks you to improve learner documentation. Treat `public_tests/` as read-only and expect additional independent tests.

## Commands

Run from this repository root:

```sh
sh environment/check.sh
make -C starter clean all
make -C starter public
```

## Engineering constraints

- Use C11 and keep `-Wall -Wextra -Wpedantic -Werror` clean.
- Do not allocate dynamically, use global mutable state, spawn subprocesses, consult a clock, or perform host file I/O from the kernel model.
- Preserve the constants and public declarations in `starter/include/pebble.h`; independent tests compile against that interface.
- Treat every mutating API as a state-machine transition. On an error, leave observable state unchanged unless `REQUIREMENTS.md` explicitly says otherwise.
- Avoid undefined behavior: validate IDs, slots, ranges, lengths, pointers, integer additions, and permissions before dereferencing or copying.
- Keep diagnostics deterministic. `pebble_check()` must not mutate the model.
- Do not add credentials, machine-specific absolute paths, generated binaries, or copied upstream material.

Commit-equivalent checkpoints should correspond to the milestones in `REQUIREMENTS.md`. Record design choices in your own notes before implementing them; do not weaken tests to fit an implementation.
