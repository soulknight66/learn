# Comprehension Response

Unit: `managed_unit_01_relational_pipeline`

## 1. Pull trace and early stopping

Assume this input schema and ordered scan input:

```text
(id INT, team TEXT, score INT)
(7, "blue", 12)
(3, "red",   5)
(9, "blue",  8)
(4, "blue", 12)
(6, "red",  20)
```

The pipeline is:

```text
Scan
  -> Filter(team = "blue")
  -> Filter(score > 8)
  -> Project(id, score)
  -> Limit(2)
```

On the first root pull, scan emits `(7,"blue",12)`. Both filters emit it, projection emits `(7,12)`,
and limit emits `(7,12)`.

On the second root pull, the score filter asks its child for another qualifying row. Scan emits
`(3,"red",5)`, which the team filter rejects. Scan then emits `(9,"blue",8)`; the team filter emits it,
but the score filter rejects it. Scan next emits `(4,"blue",12)`. Both filters emit it, projection
emits `(4,12)`, and limit emits its second row, `(4,12)`.

The emissions through that point are therefore:

| Stage | Rows emitted, in order |
| --- | --- |
| Scan | `(7,"blue",12)`, `(3,"red",5)`, `(9,"blue",8)`, `(4,"blue",12)` |
| `team = "blue"` | `(7,"blue",12)`, `(9,"blue",8)`, `(4,"blue",12)` |
| `score > 8` | `(7,"blue",12)`, `(4,"blue",12)` |
| `Project(id, score)` | `(7,12)`, `(4,12)` |
| `Limit(2)` | `(7,12)`, `(4,12)`, then EOS |

The final schema is `(id INT, score INT)`. When the caller asks again, limit already has a count of
two and returns EOS without pulling projection or either filter. Consequently the fifth input row,
`(6,"red",20)`, is never requested from scan. The caller then closes the root in `finally`.

## 2. Row validation and lifecycle misuse

Row construction must compare the row with its schema before storing it. The value count must equal
the column count, every `INT` cell must be an `Integer`, every `TEXT` cell must be a `String`, and no
cell may be null. The constructor snapshots the values so a caller cannot mutate a valid row after
validation. Wrong arity, nulls, and wrong Java value types are row-validation errors; they are not
predicate failures or EOS.

Lifecycle checking is separate. Pulling or closing in `NEW`, opening twice, opening after close, or
pulling after close throws a lifecycle exception. Pulling after natural exhaustion is legal and
returns stable EOS. Closing after a successful open is effective once; subsequent closes are harmless
no-ops. This distinction identifies whether the data was malformed or the operator protocol was
misused.

## 3. Exactly-once close on both termination paths

Natural exhaustion does not implicitly close the chain. A caller that successfully opened the root
keeps `root.close()` in a `finally` block. On natural EOS, that close moves the root to `CLOSED` and
each unary close hook propagates one close to its child. The terminal guard in `AbstractOperator`
makes a later root close a no-op, so it cannot close a child twice.

Early limit termination follows the same rule. Limit stops pulling as soon as it has emitted its
count, although its child can still be `OPEN`. The caller's `finally` close then propagates through
limit and closes that child chain once. Repeating close at the root does not propagate again. Thus
normal exhaustion and an early limit use one ownership rule; neither depends on EOS as an implicit
resource-release signal. Closing before a successful open remains an error rather than an idempotent
shortcut. The named `operator lifecycle contract` test checks stable EOS, illegal transitions, and
idempotent close. The `early close propagates exactly once` test uses a counting child on both a
partially consumed chain and a limit-terminated chain; an extra propagated close or pull changes an
exact counter assertion.

## 4. Deterministic independent oracle

The generated test records seed `0x5EEDC0DE`, creates 240 plain `GeneratedRecord` objects, and assigns
each a deterministic tag and score in `[-20, 100]`. Its oracle is one direct list loop over those plain
objects: retain scores strictly greater than 15 and strictly less than 70, append `(tag, id)`, and stop
at 37 results. Only after the oracle is complete does the test convert the records to `Row` objects and
run `Limit(Project(Filter(Filter(Scan))))` with the same boundaries and output order.

The oracle does not call `FilterOperator`, `ColumnPredicate`, projection helpers, or production
iteration code, so a shared comparison, ordering, or limiting defect cannot automatically reproduce
itself in expected output. The exact ordered value lists are compared, and an assertion first confirms
that the fixed seed actually reaches the intended limit. This can catch an off-by-one comparison at 15
or 70, or a rare ordering/limit interaction absent from small examples. Separate named tests cover
stable EOS, limit zero, no matches, a limit above the input count, schema/type rejection, and a
counting child that proves zero and exhausted limits perform no extra pull.

## 5. Production tradeoff

Snapshots, defensive copies, and unmodifiable views make ownership local and results repeatable.
They prevent caller mutation from changing schemas, rows, or scan order midway through execution.
The cost is allocation and `O(n)` scan-input retention, which is inappropriate for a large relation
that should stream from storage. Per-row projection also allocates a fresh immutable row.

Explicit diagnostic categories make failures actionable and deterministic: a schema problem, row
type mismatch, bad predicate, lifecycle misuse, and bad operator argument are not conflated. The
tradeoff is a larger public API whose exception taxonomy and messages must be maintained, translated,
and tested consistently in production.

## 6. Future disk scan contract

A disk scan should preserve the current observable contract: it publishes a stable schema, produces
records in a documented stable order, returns no more than one row per pull, and uses explicit EOS
that remains EOS on later pulls. Filters, projection, and limit should not need to know whether their
child is backed by a list or pages on disk.

Disk access makes resource and error handling more demanding. `open` may acquire a file, page cursor,
or buffer pin; early limit termination must still release it through one close cascade; and close
itself may fail. The interface therefore needs an intentional richer contract—such as a preserved
execution-error cause and an `AutoCloseable`-style resource policy—before that implementation is
added. A read, decode, or close I/O failure must be surfaced explicitly and must never be converted
to ordinary EOS, which would silently present a truncated relation as complete.

## Draft assumptions and validation status

- Operators are single-use and are closed explicitly only after a successful open.
- Supported values are non-null `Integer`/`String` instances corresponding to `INT`/`TEXT`.
- A scan preserves its constructor-list order; a shared-child operator graph is out of scope.
- The unit is dependency-free and is run through the test main documented in `RUN.md`.
- These responses and artifacts are learner-generated drafts labeled
  `LEARNER_GENERATED_UNVALIDATED`; they do not claim evaluator validation or completion of all CS186
  work.
