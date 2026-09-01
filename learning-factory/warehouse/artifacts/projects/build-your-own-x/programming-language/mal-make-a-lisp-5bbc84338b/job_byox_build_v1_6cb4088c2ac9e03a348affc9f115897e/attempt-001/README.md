# Sprig: build a small Lisp twice

Sprig is a standalone language-construction challenge inspired only by the catalog topic “make a
Lisp.” You will build an s-expression reader, a lexically scoped tree-walking evaluator, and a small
bytecode compiler/virtual machine. The language contract is local to this repository; no linked
tutorial content is needed.

The challenge is progressively testable:

1. **Read** source text into symbols, literals, and lists while reporting useful source locations.
2. **Evaluate** literals, calls, control flow, definitions, mutation, and short-circuit forms.
3. **Close over scope** with functions, sequential `let` bindings, recursion, and bounded execution.
4. **Compile a defined subset** to bytecode and execute it on a stack virtual machine.
5. **Integrate** a file runner and REPL with stable output and exit behavior.

Start in [REQUIREMENTS.md](REQUIREMENTS.md), then read [CONCEPTS.md](CONCEPTS.md) and
[DESIGN_QUESTIONS.md](DESIGN_QUESTIONS.md). The incomplete package is under `starter/`; public tests
are ordered by milestone. Reference implementation, deeper tests, and design answers are sealed from
the learner view.

## Quick start

The only dependency is Python 3.6 or newer.

```bash
PYTHONPATH=starter python3 -m unittest discover -s public_tests -p 'test_*.py' -v
PYTHONPATH=starter python3 -m sprig -e '(+ 20 22)'
```

The starter intentionally does not pass the suite. Implement one milestone at a time; a useful first
target is:

```bash
PYTHONPATH=starter python3 -m unittest public_tests.test_01_reader -v
```

## Repository boundary

Learner-facing files are this README, `AGENTS.md`, `MANIFEST.yaml`, `REQUIREMENTS.md`,
`CONCEPTS.md`, `DESIGN_QUESTIONS.md`, `starter/`, `public_tests/`, and `environment/`. Everything
under a directory named `sealed` is evaluator-only. Do not use sealed material while solving the
challenge.

This artifact is independently generated. The upstream URL recorded in provenance was not fetched or
copied. See `LICENSE_BOUNDARY.md` for the precise boundary. `GENERATED` and `PARTIAL` are generation
state labels, not claims that independent validation has passed.
