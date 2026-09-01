# Relational Pipeline Design

Unit: `managed_unit_01_relational_pipeline`

## Scope and assumptions

This unit is a dependency-free, in-memory Java pull pipeline in package
`edu.learningfactory.relational`. Production sources live under `src/main/java` and tests under
`src/test/java`. Operators are single-use: an operator graph can be opened once, consumed, and
closed, but not reopened. `INT` values are represented by `Integer`, `TEXT` values by `String`, and
null values are not supported.

This is a bounded kickoff unit, not a claim that a complete database execution engine or the whole
CS186 project has been implemented. The artifacts are learner-generated and have not been validated
by an evaluator.

## Immutable data model

- `DataType` is an enum with `INT` and `TEXT`, so its values have no mutable state.
- `Column` fixes a non-null name and non-null `DataType` at construction.
- `Schema` takes a defensive snapshot of its columns and exposes only an unmodifiable view. Schema
  construction validates schema-specific invariants, including invalid columns and ambiguous names.
- `Row` takes a defensive snapshot of its values and exposes only an unmodifiable view. Its
  constructor validates the value count and each value against the corresponding schema column.
  Nulls, wrong arity, and values whose Java type does not match `INT`/`TEXT` are rejected.

Because `Integer` and `String` are themselves immutable, a copied list of those values is sufficient
to keep a `Row` immutable. No caller-owned mutable collection is retained by these objects.

The public failure categories remain distinct: lifecycle misuse, invalid schemas, invalid rows,
invalid predicates, and invalid operator arguments produce their corresponding diagnostic exception
types. This makes a caller error such as a negative limit distinguishable from a row whose value has
the wrong type.

## Pull protocol

`Operator` exposes a schema and the lifecycle operations `open`, `pull`, and `close`. `pull` returns an
explicit `PullResult`: either one row or end-of-stream. End-of-stream is not represented by `null`, an
exception, or a sentinel row. Once an opened operator reports end-of-stream, later pulls also report
end-of-stream until it is closed.

`AbstractOperator` owns the common state machine:

| Current state | Operation | Resulting state and behavior |
| --- | --- | --- |
| `NEW` | `open` | Runs the subclass open hook and enters `OPEN`. |
| `NEW` | `open` hook fails | Attempts the close hook once, preserves any cleanup failure as suppressed, enters terminal `CLOSED`, and rethrows the open failure. |
| `NEW` | `pull` or `close` | Throws a lifecycle exception. |
| `OPEN` | `pull` with a row | Returns the row and remains `OPEN`. |
| `OPEN` | `pull` with EOS | Returns EOS and enters `EXHAUSTED`. |
| `OPEN` or `EXHAUSTED` | `close` | Runs the close hook once and enters `CLOSED`. |
| `EXHAUSTED` | `pull` | Returns EOS without consulting a child again. |
| `CLOSED` | `close` | No-op; close is idempotent after the first valid close. |
| `CLOSED` | `open` or `pull` | Throws a lifecycle exception; `CLOSED` is terminal. |

Exhaustion does not implicitly close an operator. Callers close the root in a `finally` block after a
successful open, whether iteration reaches natural EOS or stops at a limit. Each unary operator
propagates its one effective close to its child; repeated closes at the root do not produce repeated
child closes. A failed open is the other cleanup path: the common lifecycle wrapper gives partially
initialized subclasses one rollback attempt and makes the instance terminal so cleanup is not retried.

## Operators and validation timing

### Scan

`ScanOperator` fixes its schema and snapshots the input row list in its constructor. It validates the
input references and row schemas before execution, so later mutation of the caller's list cannot
change the result. Its single-use cursor begins at zero, and opening activates that execution. Each
pull returns the next snapshotted row in list order, then stable EOS.

### Filter

`ColumnPredicate` is constructed for a particular column operation and is validated eagerly against
the child's schema when the filter is assembled. Unknown columns, incompatible literal types, and
unsupported comparisons fail before `open`; they cannot appear only after some rows have already
escaped. `FilterOperator.pull` repeatedly pulls its child until the predicate matches a row or the
child returns EOS. Matching rows retain the child's schema and order.

### Project

`ProjectOperator` validates its requested columns against the child schema at construction. Missing,
ambiguous, or otherwise invalid selections therefore fail before execution. It constructs its output
schema eagerly and, for each child row, builds a new row in exactly the requested order.

### Limit

`LimitOperator` validates that its limit is nonnegative at construction. It returns at most that many
child rows. Once its emitted count equals the limit—including immediately for limit zero—its next and
all later pulls return EOS without pulling the child. A caller still closes the root so an early limit
also closes the not-yet-exhausted child chain.

Null children and other malformed operator constructor arguments are rejected as operator-argument
errors rather than deferred to lifecycle execution.

## Ownership and close propagation

Schemas, rows, scan inputs, selected-column specifications, and predicate literals are captured in
immutable form. Accessors return immutable objects or unmodifiable views. Unary operators own the
lifecycle of the child passed to them for the duration of execution: root `open` opens down the chain,
and root `close` closes down the chain once. A graph with shared children is outside this unit's
ownership model.

## Complexity

Let `n` be the scan input size, `w` a row/schema width, `p` the projected width, `k` the number of
child rows a filter examines to produce its next result, and `d` the operator-chain depth.

| Component/operation | Time | Additional space or note |
| --- | --- | --- |
| Schema or row construction | `O(w)` | `O(w)` defensive snapshot |
| Scan construction | `O(nw)` worst case | `O(n)` snapshot; structural schema checks can cost `O(w)` per row |
| Scan open / pull / close | `O(1)` each | Pull is `O(1)` after the constructor snapshot |
| Filter local open / close | `O(1)` | Predicate was eagerly validated |
| Filter pull | `O(k)` normally; `O(kw)` worst case | May consume through all remaining child rows; structural schema checks can cost `O(w)` |
| Project pull | `O(p)` locally; `O(w + p)` worst case | Structural contract check plus one immutable projected row |
| Limit pull | `O(1)` plus at most one child pull | Zero child pulls once the count is reached |
| Root open / close | `O(d)` | Unary propagation visits each operator once |

The tables describe local costs except where child work is stated. Thus a full root pull includes the
cost of the downstream operator calls it triggers.

## Extension seam for a disk scan

A future disk-backed scan can implement the same `Operator` contract while preserving the observable
rules: a fixed schema, stable source order, at most one row per successful pull, and an explicit,
stable EOS. It can replace the list/cursor internals with a page or record iterator without changing
filter, projection, or limit.

That extension also requires a richer resource and error contract than this bounded in-memory unit:
opening may acquire files or buffers, close must release them exactly once even after early limit
termination, and I/O failure must be reported explicitly rather than disguised as EOS. A production
design should decide whether checked failures, an operator execution exception with a preserved
cause, and/or `AutoCloseable` best expresses that contract before adding disk I/O.
