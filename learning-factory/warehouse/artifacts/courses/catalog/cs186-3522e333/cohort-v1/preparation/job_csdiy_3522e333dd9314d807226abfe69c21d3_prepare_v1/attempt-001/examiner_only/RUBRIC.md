# Independent Examiner Rubric: Relational Operator Pipeline

> Unit: `managed_unit_01_relational_pipeline` · Audience: examiner only · Validation label: `PREPARED_NOT_APPLIED`

This rubric evaluates only `managed_unit_01_relational_pipeline`. A pass is evidence for this manager-authored kickoff, never for the full catalog course.

## Evaluation protocol

Evaluate the submitted attempt, not learner claims or previously captured output. In an isolated offline workspace, have the worker harness invoke the documented clean build and test commands as argument arrays with bounded timeouts, process-group control, and captured logs. Preserve the submitted files, revision identity, command, exit status, and logs with the result. Examiner tests and this rubric must remain outside learner-facing paths.

Before scoring, verify that production source, test source, `DESIGN.md`, `RUN.md`, `SUBMISSION_MANIFEST.json`, captured test output, and a comprehension response are present. Confirm that the manifest names `managed_unit_01_relational_pipeline` and initially labels learner evidence `LEARNER_GENERATED_UNVALIDATED`.

## Hard gates

Do not award a pass if any of the following is true:

- production code does not compile or the documented test command cannot be executed in the declared environment;
- scan, filter, project, or limit is absent or the operators cannot compose through a common abstraction;
- the implementation depends on a network service or undisclosed external artifact;
- no deterministic assertions exercise the submitted implementation;
- learner-visible files contain this rubric, examiner tests, sealed references, or copied expected answers; or
- the evaluator-controlled checks were not run against the submitted revision.

Preserve the failed attempt and its logs. Do not convert a learner-authored success statement or test-output file into a passing validation result.

## Scoring

Score 100 points total.

### 1. Relational semantics and composition — 30 points

- **Scan and data model (6):** ordered immutable schema, exact row conformance, explicit end-of-stream, stable input order, and no exposed input mutation.
- **Filter (7):** correct integer `=`, `<`, `>` and text `=` behavior; column and literal compatibility is checked; order is preserved.
- **Project (6):** rejects empty, duplicate, or missing selections; output schema and row values follow requested order.
- **Limit (5):** rejects negative values, handles zero and boundary counts, never exceeds the limit, and does not pull a data row for zero.
- **Composition (6):** all four operators compose through an abstraction, produce the correct schema and order, and stop upstream work when the downstream result is complete.

### 2. Contracts, lifecycle, and failure behavior — 20 points

- **Lifecycle state model (8):** open/pull/close rules match the task, end-of-stream is stable, close is idempotent after its first valid call, and upstream close propagates once.
- **Validation and diagnostics (7):** malformed rows, names, types, predicates, limits, and lifecycle misuse fail deterministically in documented categories without silent coercion.
- **Ownership (5):** schema, rows, collections, and returned values cannot be mutated through accidental aliases, or an equally strong documented mechanism is demonstrated.

### 3. Verification quality — 20 points

- **Behavioral coverage (8):** assertions cover every required operator, full composition, stable order, none/some/all filters, projection schema, and limit boundaries.
- **Adversarial coverage (6):** invalid data, schema, predicate, argument, and lifecycle cases are asserted, including early close and stable end-of-stream.
- **Generated oracle test (4):** uses a recorded fixed seed and a genuinely independent list-based oracle across varied inputs.
- **Determinism (2):** repeated clean runs have the same result and no test relies on network, wall-clock timing, or iteration order from an unordered structure.

### 4. Software design and maintainability — 15 points

- **Separation and abstraction (6):** components have focused responsibilities; child operators are used through a narrow interface; implementation details do not leak unnecessarily.
- **Clarity (4):** names, code organization, and concise comments make contracts and non-obvious choices legible.
- **Complexity and extension reasoning (5):** `DESIGN.md` accurately analyzes time/space costs and identifies a plausible disk-scan extension seam without prematurely implementing it.

### 5. Reproducibility and comprehension — 15 points

- **Reproduction record (5):** `RUN.md` is sufficient for a clean offline run, and captured output matches the command and attributable submission revision.
- **Submission provenance (3):** the JSON manifest is valid, complete, and retains the learner-unvalidated label until the harness records a separate result.
- **Comprehension (7):** responses accurately connect observed behavior to the student's implementation and reason about validation, lifecycle, oracle independence, engineering tradeoffs, and a disk-backed extension.

## Reference observations for examiner checks

Use independent tests rather than copying learner tests. In particular:

- For the comprehension trace, the first filter emits IDs `7, 9, 4`; the second emits `7, 4`; projection emits `(7, 12), (4, 12)` under schema `(id INT, score INT)`; limit emits both. Once the second projected row is delivered, limit needs no third data pull and close must propagate once.
- A zero limit may open its child to establish the execution lifecycle, but it must not request a child row. Closing it must still close the opened chain once.
- Pull before open, double open, open after close, pull after close, and close before open must be distinguishable as lifecycle failures. Repeated close after a valid first close is a no-op; repeated pulls after end-of-stream remain end-of-stream while still open.
- Construct mutable input collections and attempt post-construction mutation to check whether scan behavior changes. The documented ownership policy must match observation.
- Include equal values, empty input, Unicode and empty text, integer extrema, projection reorder, limit larger than input, incompatible comparisons, and early termination in evaluator-controlled cases.

## Pass rule and recorded outcome

A passing result requires all hard gates, at least **75/100 overall**, at least **18/30** in relational semantics, at least **12/20** in contracts/lifecycle, and at least **12/20** in verification quality.

The recorded result must include the numeric breakdown, hard-gate decisions, validator identity/version, submitted artifact identity, commands and exit statuses, log locations, and one of these labels:

- `KICKOFF_UNIT_VALIDATED_PASS`
- `KICKOFF_UNIT_VALIDATED_FAIL`

Neither label authorizes `COURSE_COMPLETED`.
