# Pebble: a compiler from scratch

Build a compiler and bytecode virtual machine for **Pebble**, a deliberately small block-structured language. Source text must travel through four explicit stages:

```text
source -> tokens -> AST -> bytecode -> output
```

The starter exposes the required Ruby API but intentionally leaves the language machinery unfinished. The public suite is a foothold, not a complete specification; `REQUIREMENTS.md` is authoritative.

## Progression

1. Implement the lexer, including positions, comments, and longest-match operators.
2. Implement recursive-descent parsing with the documented precedence and AST schema.
3. Compile names, lexical scopes, branches, and loops into stack bytecode.
4. Execute verified bytecode with exact runtime types and bounded resources.
5. Complete the command-line driver and add tests for malformed input.

Run the visible checks with:

```sh
ruby -Istarter/lib public_tests/test_public.rb
```

Run a source file after implementation with:

```sh
ruby starter/bin/pebble path/to/program.peb
```

Ruby 2.5 or newer is sufficient; no third-party gems are required. See `CONCEPTS.md` for background and `DESIGN_QUESTIONS.md` for reflection prompts. This artifact remains `GENERATED` + `PARTIAL` until an independent harness validates it.
