# Prefix Forge: a tiny compiler in Go

Build a complete toolchain for a deliberately small prefix-expression language.
You will turn source text such as `(add 7 (mul 3 4))` into tokens, an abstract
syntax tree, checked stack-machine bytecode, and finally the value `19`. A direct
AST interpreter gives you a second execution path with which to test the compiler.

This is a challenge repository, not a tutorial with answers in the learner view.
The public contract is in [REQUIREMENTS.md](REQUIREMENTS.md), the supplied API
shapes are in `starter/`, and black-box examples are in `public_tests/`.

## Progression

1. Make lexical errors and source positions precise.
2. Parse nested calls into the supplied AST.
3. Type-check built-ins, including branch agreement for `if`.
4. Emit stack bytecode and patch conditional jumps.
5. Execute bytecode defensively and implement the direct evaluator.
6. Use differential and adversarial testing to find disagreements.

Run from the repository root:

```bash
cd starter && go test ./...
cd ../public_tests && go test ./...
```

The starter module intentionally returns `ErrNotImplemented` from core stages,
so the second command is expected to fail before you implement them. No network
dependencies are needed. See `environment/README.md` for toolchain requirements.

## Language glimpse

Programs contain one or more expressions. Literals are signed decimal integers,
quoted strings, and `true`/`false`. Calls use parentheses with a built-in name in
operator position. Examples:

```text
(print "hello")
(if (lt 2 9) (add 40 2) 0)
```

Exact grammar, built-ins, API behavior, limits, and diagnostics are normative in
`REQUIREMENTS.md`. Design prompts are intentionally separated in
`DESIGN_QUESTIONS.md`. Independent validation remains required; the checked-in
status is `GENERATED` + `PARTIAL`.
