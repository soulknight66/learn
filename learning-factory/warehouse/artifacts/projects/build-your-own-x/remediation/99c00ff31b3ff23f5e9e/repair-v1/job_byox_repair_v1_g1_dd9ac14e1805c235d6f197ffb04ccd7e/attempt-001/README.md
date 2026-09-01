# Mica: a tiny interpreter and x86-64 compiler

Mica is a standalone build-your-own-language challenge in C. You will finish a
small, deterministic language tool that tokenizes and parses source text,
executes the resulting syntax tree, and can instead emit x86-64 assembly.

The language has signed integer values, variables, arithmetic and comparisons,
`print`, `if`/`else`, and `while`. That is enough surface area to make precedence,
control flow, diagnostics, and backend design matter without hiding the ideas
behind a large runtime.

## Start here

1. Read `REQUIREMENTS.md` for the observable contract.
2. Read `CONCEPTS.md`, then answer the prompts in `DESIGN_QUESTIONS.md`.
3. Build the starter with `make -C starter`.
4. Run `python3 public_tests/test_public.py` from this directory.
5. Implement the marked stages in `starter/src/mica.c`.

The initial starter is intentionally incomplete: token inspection works, while
`run` and `compile` report that the parser/backend stages are unfinished. Public
tests therefore include expected failures until those stages are implemented.

## Command-line contract

```text
mica tokens SOURCE.mica
mica run SOURCE.mica
mica compile SOURCE.mica -o OUTPUT.s
```

`tokens` writes one normalized token per line. `run` writes only language-level
`print` output to standard output. `compile` produces GNU assembler input for an
x86-64 System V host; linking that file with the system C runtime must yield a
program whose output matches `run`.

## Repository map

- `starter/`: learner-owned implementation and examples
- `public_tests/`: deterministic black-box tests and their runner
- `environment/`: toolchain assumptions and setup checks
- `REQUIREMENTS.md`: syntax, semantics, limits, and diagnostics
- `CONCEPTS.md`: background on the implementation stages
- `DESIGN_QUESTIONS.md`: decisions to make before coding

Reference code, stronger tests, design answers, and review findings are sealed
inside the complete production pack. They are excluded from the learner-facing
projection; prose and file modes are not treated as an access boundary. The
projection tool copies only the nine allowlisted roots documented in
`environment/README.md`, and its verifier checks every projected file against a
content inventory. If a learner view contains `sealed/`, it is invalid. The
linked catalog item is provenance only; this challenge was written
independently.

## Scope and status

The artifact status is `GENERATED` + `PARTIAL`. Local commands and their actual
results are recorded in `VALIDATION.md`, but independent harness validation is
still required. No production-readiness claim is made.
