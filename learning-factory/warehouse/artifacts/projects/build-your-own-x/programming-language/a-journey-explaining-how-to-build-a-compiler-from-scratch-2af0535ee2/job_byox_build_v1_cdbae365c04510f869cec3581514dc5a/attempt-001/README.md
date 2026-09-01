# Pebble: build a small bytecode compiler in C

Pebble is a deliberately small language with enough sharp edges to teach the whole compilation
pipeline: tokenization, precedence parsing, lexical name resolution, jump patching, bytecode
execution, deterministic diagnostics, and resource limits. You will complete the compiler and virtual
machine behind a fixed C API and command-line interface.

The language uses signed 64-bit integers; zero is false and every nonzero value is true. A program can
declare and assign block-scoped variables, print values, branch, and loop:

```text
let n = 6;
let product = 1;
while (n > 1) {
  product = product * n;
  n = n - 1;
}
print product;
```

## Suggested progression

1. Build the starter and make the literal/`print` public cases pass.
2. Add the scanner and precedence ladder for arithmetic and comparisons.
3. Resolve scoped variables, including shadowing and assignment.
4. Emit and patch conditional and loop jumps; preserve short-circuit semantics.
5. Execute bytecode with checked arithmetic, stack validation, and a deterministic step budget.
6. Harden cleanup and diagnostics, then run all public tests under sanitizers if your host provides
   them.

Start with `REQUIREMENTS.md`, use `CONCEPTS.md` as a map, and answer `DESIGN_QUESTIONS.md` before
coding control flow. The starter intentionally builds but reports that compilation is not implemented.

```sh
make -C starter
PEBBLE_BIN=starter/build/pebble python3 public_tests/test_cli.py
```

Passing public tests is necessary, not sufficient. Independent validation remains required. This pack
is labeled `GENERATED` and `PARTIAL`; see `VALIDATION.md` for commands actually observed on its build
host.
