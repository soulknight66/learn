# Mica: build a tiny Pascal compiler and virtual machine

Mica is a deliberately small, deterministic programming language. Your task is to
finish a compiler written in Pascal. It must tokenize and parse Mica source,
compile it to stack-machine bytecode, and execute that bytecode.

This is an independent educational challenge inspired only by the catalog topic
“Let's Build a Compiler.” The linked article is provenance, not copied course
material. See `LICENSE_BOUNDARY.md` and `PROVENANCE.json`.

## The language at a glance

```text
# Euclid's algorithm
let a = 1071;
let b = 462;
while b != 0 {
  remainder = a % b; # assignment requires an existing variable
  a = b;
  b = remainder;
}
print a;
```

The example intentionally contains a mistake: `remainder` has not been
declared. Correct it with `let remainder = a % b;`. The compiler must reject the
original rather than silently creating a variable.

Mica supports integer literals, variables, `let`, assignment, `print`, `if` /
`else`, `while`, `halt`, arithmetic, comparisons, unary negation, and logical
not. Details and normative behavior are in `REQUIREMENTS.md`.

## Suggested path

1. Read `REQUIREMENTS.md` and `CONCEPTS.md`.
2. Build the scaffold in `starter/`.
3. Implement lexing, then precedence parsing and bytecode emission, then the VM.
4. Run `public_tests/run_tests.py` against your executable.
5. Consider the questions in `DESIGN_QUESTIONS.md` before extending the language.

The starter is incomplete by design. Public tests describe only public behavior;
independent validators may exercise additional valid programs and malformed
inputs. Do not special-case the examples.

## Quick start

With Free Pascal (`fpc`) available:

```bash
cd starter
make
cd ..
MICA_BIN="$PWD/starter/bin/mica" python3 public_tests/run_tests.py
```

Or use `environment/check.sh`, which detects a missing compiler and exits with a
clear diagnostic.

## Repository boundary

Learner material is confined to the root learning documents plus `starter/`,
`public_tests/`, and `environment/`. Reference implementation, deeper tests,
answers, reviews, and production analysis are sealed and are not prerequisites
for solving the challenge.

Generation status is `GENERATED` + `PARTIAL`: this host did not provide a Pascal
toolchain, so independent compilation and execution remain required.
