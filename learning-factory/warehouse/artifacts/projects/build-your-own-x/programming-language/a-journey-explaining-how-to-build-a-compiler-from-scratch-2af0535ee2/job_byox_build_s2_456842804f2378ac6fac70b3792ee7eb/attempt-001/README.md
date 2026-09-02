# Sprig: build a tiny compiler in C

Sprig is a progressively revealable compiler challenge. You will finish a lexer-to-bytecode pipeline for a deliberately small language, then run the bytecode on a checked stack virtual machine. The project is independent educational material inspired only by the catalog topic “A journey explaining how to build a compiler from scratch”; no linked tutorial text or code is included.

## The language

```sprig
# bindings are immutable
let width = 6;
let area = width * 7;
print area;
print -(area - 50);
```

Sprig has signed 64-bit integers, `let` declarations, `print` statements, identifiers, parentheses, unary `-`, and the binary operators `+`, `-`, `*`, and `/`. A successful run prints one decimal integer per `print` statement.

## Start here

1. Read [REQUIREMENTS.md](REQUIREMENTS.md) for the observable contract.
2. Read [CONCEPTS.md](CONCEPTS.md), then inspect `starter/include/sprig.h` and `starter/src/`.
3. Build with `make -C starter`.
4. Run `python3 public_tests/run_tests.py --binary starter/build/sprig`.
5. Implement the compiler in `starter/src/compiler.c`, then the VM in `starter/src/vm.c`.
6. Use `starter/build/sprig --tokens FILE` and `--disassemble FILE` while debugging.
7. Answer the prompts in [DESIGN_QUESTIONS.md](DESIGN_QUESTIONS.md).

The starter intentionally compiles but is incomplete. Its lexer and CLI are supplied; non-empty programs initially report a deterministic “compiler stage is not implemented” diagnostic. Public tests disclose the core behavior, not every edge case.

## Repository boundary

Learner-facing inputs are `README.md`, `AGENTS.md`, `MANIFEST.yaml`, `REQUIREMENTS.md`, `CONCEPTS.md`, `DESIGN_QUESTIONS.md`, `starter/`, `public_tests/`, and `environment/`. Reference implementations, reference tests, design answers, and review material live under `sealed/` and must not be consulted while solving. Other top-level exercise/evaluation directories are harness-controlled material, not solution inputs.

This pack is marked `GENERATED` and `PARTIAL`: it was built and locally exercised, but the learning-factory’s independent validator—not this document—decides any stronger validation label.
