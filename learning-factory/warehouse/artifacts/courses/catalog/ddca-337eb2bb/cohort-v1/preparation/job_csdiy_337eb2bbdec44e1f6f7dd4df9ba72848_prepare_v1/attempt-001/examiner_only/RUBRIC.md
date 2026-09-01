# Independent examiner rubric: Combinational Logic as a Tested Interface

This rubric is examiner-only. Score the submitted artifacts and independently observed behavior; do not accept a learner's prose claim or pasted output as proof. The maximum is 100 points. Recommend kickoff-unit completion only at 80 or more points **and** with every critical gate satisfied.

Passing this rubric concerns only `manager_unit_01_combinational_contracts`. It must never be promoted into evidence of an official ETH Zurich unit, lab, or whole-course completion.

## Controlled examination procedure

1. Preserve the learner submission as durable evidence. Perform any generated checks in harness-owned scratch space.
2. Confirm the six required artifacts exist. Record their hashes or the attempt artifact location.
3. Read the learner's documented command, then execute it with an argv-based, bounded-time harness from the documented project root. Capture stdout, stderr, and exit status.
4. Independently import `full_adder` and `ripple_add4`. Exercise all valid cases: 8 one-bit combinations and 512 four-bit combinations. Derive expected values with ordinary integer arithmetic in examiner code.
5. Exercise invalid values independently, including booleans, strings, floats, `None`, negative integers, and integers just above each allowed range. Require `ValueError` for every invalid argument position.
6. Inspect production code to confirm bit-level logic and four-stage carry chaining. Do not infer composition merely from correct outputs: reject a whole-number arithmetic lookup or shortcut that bypasses the required design.
7. Inspect the learner tests to confirm they enumerate the domains, use an independently expressed oracle, assert output type/range, check invalid values, and contain an intentional propagation case.
8. Compare `EVIDENCE.md` with the controlled rerun. Treat materially fabricated execution claims as a critical failure; preserve discrepancies.

Examiner checks and any hidden cases remain outside the student-safe tree.

## Critical gates

All of the following are mandatory:

- The required API imports without side effects, and all six required artifacts are present.
- Every independently checked valid-domain case satisfies the contract with integer (not Boolean) outputs in range.
- Representative invalid inputs in every argument position raise `ValueError`.
- `ripple_add4` implements four ordered one-bit stages with carry-out from one stage feeding carry-in of the next; it does not compute the answer by whole-number addition, `sum`, `divmod`, a table, or an equivalent bypass.
- Learner tests genuinely cover all 8 and 512 valid calls and use a test oracle independent of the production equations.
- Execution evidence is not fabricated.

A failed gate means `NOT_YET_COMPLETE` regardless of points. Record the exact failure and retained evidence so a later attempt can address it.

## Scoring

### 1. Contract and design reasoning — 15 points

- 4: complete, internally consistent eight-row table with integer-bit outputs;
- 4: correct sum and carry equations, with notation defined and tied to the table;
- 3: clear least-to-most-significant composition and carry-flow explanation;
- 2: correct fixed-width arithmetic invariant and invalid-input policy; and
- 2: useful traceability from contract clauses to named code/tests.

### 2. Production implementation — 25 points

- 7: `full_adder` uses correct bit-level Boolean/bitwise logic;
- 9: `ripple_add4` performs exactly four ordered stages and constructs the result from returned sum bits;
- 5: all domain/type validation is complete, consistent, and performed before circuit work; and
- 4: code is deterministic, focused, readable, and free of third-party dependencies and observable side effects.

### 3. Verification quality — 25 points

- 7: all 8 one-bit cases are systematically covered;
- 8: all 512 four-bit cases are systematically covered against a test-only arithmetic oracle;
- 4: tests assert integer output types and output ranges;
- 4: invalid-input tests cover argument positions and the specified type/range classes; and
- 2: a clearly named, intentional carry-propagation test adds diagnostic value beyond the exhaustive loop.

Do not award exhaustive-coverage points for a claimed count without inspectable enumeration or equivalent deterministic generation.

### 4. Reproducibility and engineering evidence — 15 points

- 4: README gives scope, layout, supported Python, and an exact root-relative test command;
- 5: the documented command completes under the bounded examiner rerun and agrees with recorded status;
- 3: evidence identifies Python version, execution context, exit status, and clean-root rerun; and
- 3: limitations and failures are reported honestly, with no reliance on an editor, undeclared package, or external course material.

### 5. Comprehension — 20 points

Award up to 2.5 points per prompt using the following answer indicators. Equivalent well-reasoned formulations are acceptable.

1. Derives `sum = a XOR b XOR carry_in`; derives carry as a majority-of-three expression such as `(a AND b) OR (a AND carry_in) OR (b AND carry_in)`; justifies against all combinations or parity/majority semantics.
2. Computes `2^3 = 8` for three bit inputs and `16 * 16 * 2 = 512` for two four-bit operands and one carry bit.
3. Shows a carry entering every higher stage for `15 + 1`: four zero sum bits and final carry one; connects this to a fixed-width result of zero and total value 16.
4. Supplies and correctly analyzes a distinguishing case. For example, `(0, 0, 1)` exposes reuse of the original carry in higher stages, while `(1, 1, 0)` exposes failure to propagate the generated low-bit carry.
5. Identifies correlated/common-mode error from duplicated logic; explains representational diversity of the arithmetic oracle; notes a remaining risk such as a wrong public contract, wrong domain enumeration, or shared test harness defect.
6. Distinguishes Python's inheritance/coercion behavior from the explicitly narrow integer-bit API; notes that rejection prevents accidental semantic inputs and keeps evidence/types unambiguous.
7. Identifies the least-significant-to-most-significant carry chain as the longest dependency, with delay growing with width; makes a sound comparison to sequential dependencies and may mention a prefix/carry-lookahead alternative.
8. Names inspectable artifacts, independent test execution, examiner results, and honest evidence; explicitly limits the inference to the manager-authored kickoff because official materials and remaining course topics/labs were not completed or validated.

For each response, award full credit only when both the conclusion and reasoning are present. A bare result earns at most half credit.

## Decision record

The examiner record must include the section scores, total, each critical-gate result, controlled command outcome, artifact/evidence location, and a bounded disposition of `READY_FOR_VALIDATOR` or `NOT_YET_COMPLETE`. Only the worker-harness-controlled validator may convert that disposition into job success.
