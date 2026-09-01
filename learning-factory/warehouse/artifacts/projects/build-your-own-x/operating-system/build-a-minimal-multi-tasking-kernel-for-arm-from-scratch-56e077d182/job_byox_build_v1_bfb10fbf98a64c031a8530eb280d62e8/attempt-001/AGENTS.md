# Learner and automation guide

Work only in this challenge workspace. Treat `REQUIREMENTS.md` as the behavioral authority and the
public header as the ABI authority.

## Editable scope

Implement the TODOs in `starter/src/kernel.c` and, for the optional hardware milestone, the files
in `starter/arm/`. You may add private local tests, but do not weaken or rewrite supplied tests.

## Determinism and safety rules

- Use no dynamic allocation in kernel operations.
- Select the lowest available slot/frame/block whenever the requirements say "lowest".
- Validate an entire multi-byte VM operation before changing memory.
- Preserve old file contents when replacement cannot be completed.
- Reclaim every mapped frame when a task exits or is killed.
- Avoid undefined behavior: validate lengths and address addition before pointer arithmetic.
- Compile as C11 with `-Wall -Wextra -Werror -pedantic`.

## Useful commands

```sh
make -C starter clean all
make -C public_tests clean test
make -C public_tests clean test SANITIZE=1
```

An ARM build additionally needs an `arm-none-eabi-*` toolchain. Do not claim or record an emulator
result unless you actually observed it.

## Handoff

Report exact commands and outcomes. A worker response is not evidence that tests passed; only the
validator harness may promote the job.
