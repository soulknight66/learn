# Study Task: A NAND-Only Boolean Component Library

## Timebox and goal

Timebox this work to about six hours. Build a small Boolean component library, its exhaustive tests, and the engineering documentation needed for another person to reproduce and audit your result.

This is a standalone exercise. Do not depend on or claim conformance with an unavailable official Nand2Tetris specification.

## Component contract

Use exactly two logical input values: false and true. Your public library must expose these five operations (equivalent names are acceptable if you document the mapping):

- `nand(a, b)`: the sole trusted primitive;
- `not_gate(a)`;
- `and_gate(a, b)`;
- `or_gate(a, b)`; and
- `mux2(a, b, select)`, which chooses `a` when `select` is false and `b` when `select` is true.

State whether the public interface accepts only your language's Boolean type or also accepts `0` and `1`. Specify what happens for values outside that domain. Tests must follow the documented policy.

## Construction constraint

The body of `nand` may use the host language's built-in operations. Every derived component must be composed only by calling `nand` and/or other derived components.

Outside `nand`, do not implement Boolean behavior with host-language logical or bitwise operators, arithmetic, conditionals, pattern matching, lookup tables, casts that compute the answer, or library gate functions. Ordinary assignment, naming, calls, and returns are allowed. Keep the primitive visibly isolated so a reviewer can audit this constraint.

Tests are independent of the implementation and may use normal language features to define expected results.

## Required work

1. **Specify before composing.** Document each operation's inputs, output, behavior, invalid-input policy, and dependencies. Draw a small dependency DAG; it must not contain a cycle.
2. **Implement the library.** Keep the interfaces small and the primitive boundary obvious. Favor readable intermediate names over unexplained compression.
3. **Verify the finite domain.** Test all four input pairs for `nand`, all two inputs for `not_gate`, all four input pairs for both `and_gate` and `or_gate`, and all eight input triples for `mux2`. Expected values must come from a test oracle independent of the implementation under test.
4. **Demonstrate test sensitivity.** Temporarily introduce one plausible fault, show that the suite reports a failure, restore the correct implementation, and capture the final passing run. Do not leave the fault in the submitted source.
5. **Make it reproducible.** Provide one documented, non-interactive command that runs the complete deterministic suite from a clean checkout using only declared requirements. Avoid network access during the test run.
6. **Explain the evidence.** Complete the prompts in `COMPREHENSION.md` in your own words.

## Submission layout

Place your work in a `submission/` directory with:

- `README.md`: language/tool version, setup, the one-command test procedure, interface mapping, and assumptions;
- `src/`: implementation source;
- `tests/`: deterministic tests with readable case names or diagnostics;
- `DESIGN.md`: contracts, dependency DAG, NAND-only self-audit, and a short correctness argument;
- `evidence/test-run.txt`: the complete final passing command and output;
- `evidence/mutation-check.txt`: the fault introduced, the affected case, failing output, restoration step, and subsequent passing result; and
- `COMPREHENSION_RESPONSES.md`: numbered responses matching `COMPREHENSION.md`.

Generated caches, dependency directories, binaries, secrets, and copied course materials do not belong in the submission.

## Definition of done

Before handing off, confirm that:

- the documented command terminates successfully and runs every required case;
- repeated runs produce the same result;
- no derived component bypasses the NAND-only constraint;
- the captured evidence agrees with the final source and tests;
- a reviewer can trace every component contract to tests; and
- your documentation clearly limits the claim to this kickoff.

These checks make the work ready for examination; they do not themselves award completion.
