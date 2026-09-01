# Minnow: source text to deterministic bytecode

Build a compiler and virtual machine for Minnow, a deliberately small block-structured language. The
project crosses the whole boundary from characters to executable instructions: tokenize source,
construct an AST with precedence, resolve lexical names, emit a binary instruction stream, validate
control flow, and run it on a stack machine.

The result is not native CPU code. Minnow's target is a precisely specified portable virtual machine,
which makes instruction encoding and machine safety observable without requiring an assembler or a
platform-specific linker.

## Start here

1. Read `REQUIREMENTS.md` for the normative language and binary format.
2. Read `CONCEPTS.md`, stopping before each reveal when you want to choose a design yourself.
3. Implement the TODOs in `starter/minnow/` one stage at a time.
4. Run the public tests after every stage.
5. Answer `DESIGN_QUESTIONS.md` before comparing designs after evaluation.

No third-party packages are required. Python 3.10 or newer is required. On the generation host, use the
explicit Python 3.11 path documented in `environment/README.md`; the unqualified `python3` is too old.

## Milestones

- **A — Front end:** locations, comments, maximal-munch operators, precedence, and useful errors.
- **B — Meaning:** block scopes, duplicate declarations, and assignment to the nearest declaration.
- **C — Back end:** stack effects, local slots, absolute jump patching, and binary serialization.
- **D — Machine:** structural verification, deterministic signed arithmetic, and bounded execution.
- **E — Interface:** reproducible `compile`, `run`, and `exec` commands with stable failures.

The starter is intentionally incomplete. A clean initial public-test run is not expected. Completion
claims require independent validation; `MANIFEST.yaml` deliberately remains `GENERATED` + `PARTIAL`.

## Commands

```bash
PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m minnow compile program.mno program.mbc
PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m minnow run --max-steps 100000 program.mbc
PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m minnow exec --max-steps 100000 program.mno
```

CLI diagnostics go to standard error and use exit status 2. Successful program output consists of one
base-10 integer per `print` statement.
