# Build Your Own Shell

Build `minish`, a small POSIX-oriented command interpreter in C. The project is deliberately split at system-call boundaries: lex input, parse a pipeline, construct file descriptors, create a process group, and wait for foreground work. You will see why a shell is both a language implementation and a process supervisor.

This is an independently authored challenge. It does not reproduce the linked tutorial. The upstream link is catalog provenance only; see `PROVENANCE.json` and `LICENSE_BOUNDARY.md`.

## Progression

1. Implement the lexer and make the public lexical tests pass.
2. Turn tokens into an owned pipeline structure and reject malformed input.
3. Execute one foreground command and return its status.
4. Connect multi-command pipelines and redirections without leaking descriptors.
5. Add process groups, terminal handoff, background launch, and nonblocking reaping.
6. Implement the required built-ins in the shell process.

The exact behavioral contract is in `REQUIREMENTS.md`; the supplied interface and TODOs are in `starter/`. Public tests intentionally cover only a representative subset. Passing them is a milestone, not completion.

## Quick start

From the repository root:

```sh
make -C starter
public_tests/run.sh starter
```

The starter is expected to compile before its TODOs are implemented, but its tests initially fail. The test runner accepts an implementation directory so you can keep experimental implementations elsewhere without modifying the tests.

## Scope and safety

`minish` is an educational shell, not a secure command sandbox. It deliberately omits command substitution, globbing, variables, here-documents, aliases, shell scripts, and security isolation. Do not run untrusted commands through it.

Generated status remains `GENERATED` + `PARTIAL`. Independent validation is required, and no prose claim in this pack promotes that status.
