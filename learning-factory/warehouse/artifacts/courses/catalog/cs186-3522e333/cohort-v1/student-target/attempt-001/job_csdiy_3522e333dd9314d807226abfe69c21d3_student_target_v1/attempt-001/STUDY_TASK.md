# Study Task: Contract-Driven Relational Operator Pipeline

> Unit: `managed_unit_01_relational_pipeline` · Classification: manager-authored kickoff · Validation label: `PREPARED_NOT_LEARNER_VALIDATED`

## Goal

Build a small Java library that executes a typed, in-memory relational pipeline one row at a time. The useful product is not just working operators: it is a subsystem whose behavior, misuse cases, tests, and reproduction steps are clear to a maintainer who did not write it.

Do this work in your submission workspace, not inside `student_safe/`.

## Required model

Use the following deliberately narrow model:

- A schema is an ordered, immutable list of columns. Column names are unique. Each column has type `INT` (signed 32-bit integer) or `TEXT` (Java string).
- A row is immutable and conforms exactly to one schema: same arity, order, and value types. Null values are outside this unit.
- End of stream must have an explicit representation and must not be confused with a valid row.
- A source scan emits a finite input sequence in its original order.

Choose your own package names and concrete API, but make the operator lifecycle observable and document it. It must support these semantics:

- `open` starts one execution. Opening an already opened or closed operator fails predictably.
- pulling a row is valid only while open;
- after end of stream, later pulls continue to report end of stream;
- the first `close` releases the upstream chain exactly once, including after early termination; and
- repeated `close` calls are harmless. Closing before `open` fails predictably.

Do not silently coerce types, ignore missing columns, or repair malformed rows. State where validation occurs and keep that choice consistent.

## Required operators

Implement four composable operators:

1. **Scan** — emits supplied rows in input order and does not expose them to mutation.
2. **Filter** — retains rows using column-to-literal predicates. Support integer `=`, `<`, and `>` and text `=`. Chaining filters is sufficient; a boolean-expression parser is not required.
3. **Project** — selects and reorders a nonempty list of distinct existing columns. Its output schema and rows must follow the requested order.
4. **Limit** — emits at most a nonnegative number of upstream rows. A zero limit must not pull a data row from upstream, and early closure must still propagate.

At minimum, a pipeline such as `Limit(Project(Filter(Scan)))` must work without any operator knowing the concrete class of its child.

## Engineering constraints

- Keep production code separate from test code.
- Use no network service, database server, SQL parser, or unrecorded downloaded dependency.
- Do not add joins, storage, concurrency, or optimization to this unit.
- Give public components focused responsibilities; avoid one class that owns the entire pipeline.
- Document ownership of schemas, rows, input collections, and returned values.
- Report the time and auxiliary-space cost of each operator's `open`, pull, and `close` behavior in terms of rows and columns where relevant.
- Make error behavior specific enough for automated tests to distinguish lifecycle, schema, predicate, type, and argument failures.

## Required tests

Create deterministic automated tests that cover at least:

- each operator alone and all four in one pipeline;
- stable ordering when several rows have equal values;
- filters that retain none, some, and all rows;
- projection reorder and output-schema correctness;
- limits of zero, one, exactly the input size, and greater than the input size;
- malformed rows, duplicate or missing projected columns, incompatible predicates, and a negative limit;
- pull-before-open, double-open, pull-after-close, repeated pull after end of stream, repeated close, and close-before-open;
- early downstream close propagating upstream once;
- absence of unintended input mutation; and
- a fixed-seed generated test that compares a composed pipeline with a simple independent list-based oracle.

Tests must fail visibly on a mismatch. A printed example with no assertion is not a test.

## Deliverables

Submit:

- Java production source under a conventional source directory;
- automated test source under a separate conventional test directory;
- `DESIGN.md` describing component boundaries, lifecycle state transitions, validation timing, ownership, error taxonomy, complexity, and one realistic extension seam;
- `RUN.md` listing environment assumptions and exact clean build and test commands;
- `SUBMISSION_MANIFEST.json` containing the unit ID `managed_unit_01_relational_pipeline`, implementation language and runtime, build/test commands, submitted file paths, and the label `LEARNER_GENERATED_UNVALIDATED`; and
- `COMPREHENSION_RESPONSE.md` containing your answers to the separate comprehension prompt; and
- a fresh captured test-output file produced by the documented command.

The captured output is useful provenance, but it is not a substitute for an evaluator rerunning the submission.

## Finish line

Before submitting, start from a clean build state, run exactly the commands in `RUN.md`, capture the output, and check that another person can understand all public behavior without reading your tests first. Then answer the questions in `COMPREHENSION.md` in a separate response document.
