# Minish: build a process-aware POSIX shell

This challenge asks you to build `msh`, a deliberately small shell in C. The
interesting work is not a prompt: it is turning text into an execution plan,
constructing pipelines without leaking file descriptors, and transferring the
terminal between process groups safely.

The repository is progressively revealable:

1. Read [REQUIREMENTS.md](REQUIREMENTS.md) for the observable contract.
2. Use [CONCEPTS.md](CONCEPTS.md) to review the operating-system model.
3. Build the scaffold in `starter/` and run the black-box checks in
   `public_tests/`.
4. Answer [DESIGN_QUESTIONS.md](DESIGN_QUESTIONS.md) before implementing each
   milestone.
5. Treat `sealed/` and the harness-only directories as instructor material.

## Milestones

- **M0 — loop:** accept `-c`, batch input, blank lines, and EOF.
- **M1 — syntax:** tokenize words, quoting, escapes, pipes, redirections, and a
  trailing background marker.
- **M2 — processes:** execute commands and return accurate status codes.
- **M3 — pipelines:** wire arbitrary-length pipelines and close every unused
  descriptor in every process.
- **M4 — built-ins:** make stateful commands affect the shell process.
- **M5 — jobs:** group a pipeline, reap children, implement `jobs` and `fg`,
  and transfer the controlling terminal when interactive.
- **M6 — hardening:** handle malformed input, interrupted system calls, and
  resource failures without corrupting shell state.

## Quick start

```sh
make -C starter CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
MSH_BIN="$PWD/starter/msh" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 public_tests/test_shell.py
```

The starter is expected to compile and fail behavioral tests until you fill in
the marked work. Tests accept any implementation whose behavior matches the
contract; no reference source is needed.

## Scope

This is an educational, single-user shell, not a drop-in replacement for a
system shell. Expansion, globbing, command substitution, here-documents,
compound commands, and scripting constructs are intentionally excluded.
See `VALIDATION.md` for generator-side evidence; independent validation is
still required.
