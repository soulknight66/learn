# Study task: a tested four-bit ripple-carry adder

## Goal and boundary

Create a small Python project that models a one-bit full adder and composes four copies into an unsigned four-bit ripple-carry adder. The production implementation must expose the bit-level design; the tests may use ordinary integer arithmetic as an independent oracle.

Timebox the work to about five hours. Do not expand the task into Verilog, FPGA synthesis, a general bit-vector package, or a larger arithmetic unit.

## Public interface contract

Create `src/adder.py` with these public functions:

```text
full_adder(a, b, carry_in) -> (sum_bit, carry_out)
ripple_add4(a, b, carry_in) -> (sum_word, carry_out)
```

For `full_adder`:

- `a`, `b`, and `carry_in` are each exactly one integer bit: `0` or `1`;
- the two returned values are integer bits; and
- the result represents the arithmetic sum of the three inputs.

For `ripple_add4`:

- `a` and `b` are integers in the inclusive range `0..15`;
- `carry_in` is an integer bit;
- `sum_word` is in `0..15`, and `carry_out` is an integer bit; and
- `sum_word + 16 * carry_out` equals `a + b + carry_in`.

Python booleans are not accepted as integers for this interface. If any argument has the wrong type or lies outside its stated domain, raise `ValueError`. Validate inputs before doing circuit work.

## Design constraints

- Implement `full_adder` using Boolean or bitwise operations on bits.
- Implement `ripple_add4` by invoking the one-bit behavior once for each of four positions, from least significant to most significant, and passing each stage's carry to the next stage.
- In production code, do not calculate the result with whole-number addition, `sum`, `divmod`, or another arithmetic shortcut. Construct the output word from the four returned sum bits.
- Keep production code deterministic and free of input/output, global mutable state, and third-party dependencies.
- Make the implementation readable enough that a reviewer can trace each contract statement to code and tests.

## Required project artifacts

Submit this structure:

```text
README.md
design.md
src/adder.py
tests/test_adder.py
answers.md
EVIDENCE.md
```

`README.md` must state the scope, supported Python version, layout, and exact commands needed to run the tests from the project root.

`design.md` must contain:

- the complete eight-row one-bit input table, produced by you;
- your Boolean equations and notation;
- a description of bit ordering and carry flow across four stages;
- the invariant that connects inputs, the fixed-width result, and carry-out;
- the invalid-input policy; and
- a short traceability map from contract clauses to implementation and tests.

`src/adder.py` must contain the two public functions and any small validation helpers you need. Keep the required function signatures unchanged.

`tests/test_adder.py` must use Python's standard-library `unittest` and must:

- cover all eight valid calls to `full_adder`;
- cover all 512 valid calls to `ripple_add4`;
- derive expected valid-domain behavior from a test-only arithmetic oracle, not from the production Boolean equations;
- verify output types and ranges, not only numeric equality;
- include representative wrong types, booleans, negative values, and values above each input range; and
- contain at least one focused carry-propagation test whose purpose is clear from its name.

`answers.md` must answer every prompt in `COMPREHENSION.md`. Show reasoning; a bare value or yes/no response is insufficient.

`EVIDENCE.md` must record:

- the exact test command used;
- the Python version and relevant environment assumptions;
- the real observed test summary and exit status;
- whether the command was rerun from a clean project root; and
- any failure, untested claim, or limitation that remains.

Do not claim a command passed unless you actually ran it. A failure honestly captured with a diagnosis is better evidence than an invented success.

## Verification workflow

Use a reproducible standard-library command from the project root, such as:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

After the first successful run, review the test output, remove accidental dependencies on your current directory or editor, rerun the documented command from the project root, and paste or summarize that actual result in `EVIDENCE.md`.

Your tests are necessary evidence, but they are not the final authority. An examiner will independently inspect the composition and exercise the public interface.
