# Build Pebble Lisp

Pebble Lisp is a compact, independently designed Lisp challenge. You will turn a string into syntax,
evaluate that syntax with lexical scope, and expose the result through a small command-line program.
The core has deliberately few forms, so the difficult parts are visible: token boundaries, recursive
descent, environment ownership, evaluation order, closures, tail calls, and useful failures.

This pack is inspired only by the catalog topic “mal - Make a Lisp.” Its catalog record comes from a
CC0-1.0 catalog snapshot. The linked resource has license classification `NOASSERTION` and is provenance
only. Linked content was not retrieved, copied, or paraphrased; this includes its source, tests, prose,
examples, naming scheme, and step sequence. This pack was generated independently for personal educational
use; that origin statement does not assert a license for, or grant rights in, the linked resource.

## What you build

Implement the TODOs in `starter/pebble/` until the public contract passes. Your interpreter must support:

- integers, strings, booleans, `nil`, symbols, lists, comments, and quote syntax;
- `quote`, `if`, `do`, `def`, `let`, and `fn` special forms;
- lexical closures and constant-stack tail calls;
- the built-ins listed in `REQUIREMENTS.md`; and
- expression, file, and interactive CLI modes.

The language is intentionally not a clone of any existing implementation. `REQUIREMENTS.md` is the
authority when familiar Lisp dialects disagree.

## Suggested reveal order

1. Read `CONCEPTS.md`, then implement tokenization and reading.
2. Add environments and literal/symbol evaluation.
3. Add special forms one at a time in the order specified.
4. Add calls, closures, built-ins, and tail-call behavior.
5. Finish the CLI and exercise error paths.
6. Consider the optional compiler questions in `DESIGN_QUESTIONS.md`.

Run the public suite from this directory:

```bash
PEBBLE_PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
TMPDIR=environment "$PEBBLE_PYTHON" environment/check_runtime.py
PYTHONDONTWRITEBYTECODE=1 TMPDIR=environment PYTHONPATH=starter \
  "$PEBBLE_PYTHON" -m unittest discover -s public_tests -v
```

The starter is intentionally incomplete, so failures are expected before implementation. No third-party
packages are required. `TMPDIR=environment` gives restricted workspaces a known writable temporary
location; the supplied tests remove each temporary file they create. The runtime check exits before test
discovery with a clear error if the selected interpreter is older than 3.11 or cannot create temporary
files. The sealed material is validator/instructor material and must not be consulted as part of the
learner exercise.

The combined pack also contains `adversarial/`, `benchmarks/`, `debugging/`, and `review_exercises/`.
Those supplemental roots are instructor-only and are deliberately absent from the exported core learner
view; this pack defines no later learner reveal stage for them. A delivery harness must not give learners
the combined pack.

## Completion boundary

Passing public tests is necessary but not sufficient. Check every normative item in `REQUIREMENTS.md`,
add your own malformed-input and deep-recursion tests, and keep diagnostics deterministic. This generated
pack remains `PARTIAL` until an independent harness validates it.
