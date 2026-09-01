# Kickoff Learning Notes

Unit: `managed_unit_01_relational_pipeline`  
Status: learner-generated attempt; not compiled, runtime-tested, or evaluator-validated

## Scope boundary

I studied only the supplied kickoff brief, study task, and comprehension prompt. This work covers the
first in-memory relational-operator unit: scan, filter, project, and limit. It does not cover SQL
parsing, joins, disks, indexes, optimization, transactions, recovery, NoSQL, or the rest of CS186.

## Contract map

### Typed data

- `Schema` is an ordered immutable list of uniquely named `Column` objects.
- The supported types are exactly `INT` (`Integer`) and `TEXT` (`String`); null is rejected.
- `Row` snapshots its values and validates arity and every Java value type at construction.
- Structural schema equality permits a row made with an equivalent immutable schema, while scan and
  operator boundaries still reject a genuinely different schema.
- `PullResult` represents either one non-null row or EOS. EOS is never a null row.

### Lifecycle

The shared lifecycle is `NEW -> OPEN -> EXHAUSTED -> CLOSED`, with direct `OPEN -> CLOSED` for early
termination. Operators are single-use.

- `open` is legal only in `NEW`.
- `pull` is legal after a successful open; once EOS appears, later pulls return EOS without asking a
  child again.
- `close` before open is an error. The first close after open propagates once, and later closes are
  no-ops.
- Exhaustion and resource release are different events. The caller closes the root in `finally`, even
  after natural EOS.
- If an open hook fails, the attempt becomes terminal and receives one rollback hook. A cleanup
  failure is retained as a suppressed failure rather than replacing the original open failure.

The last rule was not needed by the simple in-memory scan, but it matters for a later file-backed
operator. Thinking about that failure path was useful production-engineering practice.

### Ownership

Schemas, rows, scan input lists, projection lists, and supported literals are immutable or copied.
Unary operators exclusively own their child lifecycle: clients operate on the root, not every node.
Shared-child graphs are intentionally out of scope because they would require reference-counted or
otherwise explicit ownership.

## Operator behavior

- `ScanOperator` snapshots row references (safe because rows are immutable) and preserves input order.
- `ColumnPredicate` binds a column index and validates the comparison before execution. Integers allow
  `=`, `<`, and `>`; text allows only `=`.
- `FilterOperator` may consume several child rows for one output but never reorders matches.
- `ProjectOperator` rejects empty, duplicate, or absent names and creates a schema and row in requested
  order.
- `LimitOperator` never pulls after reaching its nonnegative bound. In particular, limit zero opens and
  later closes its child but pulls zero rows.

## Complexity notes

The algorithms are simple, but contract checks affect their real cost. Scan construction is `O(nw)`
in the worst case because each of `n` rows may require a structural width-`w` schema comparison, while
its pull is `O(1)`. A filter pull that examines `k` rows is normally `O(k)` and worst-case `O(kw)` with
structural contract checks. Projection allocates `O(p)` values for `p` selected columns. Root open and
close traverse operator depth `d`, so both are `O(d)`.

## Test strategy drafted

The dependency-free test main contains 13 named groups. They cover individual and composed operators,
ordering, every supported predicate kind, projection schema/type order, limit boundaries, typed
failures, lifecycle misuse, stable composed EOS, failed-open rollback, exact close propagation,
ownership, and a fixed-seed oracle.

The generated oracle uses seed `0x5EEDC0DE`, 240 plain records, direct conditions `score > 15` and
`score < 70`, projection `(tag, id)`, and limit 37. Expected values are computed before creating any
operator or predicate, which reduces the chance of copying a production defect into the oracle.

These tests are authored but unrun here because neither `javac` nor `java` is installed. That is an
important distinction: test source is a hypothesis about behavior, while a successful controlled run
would be evidence.

## Main lessons

1. The difficult part of an iterator pipeline is not its asymptotic algorithm; it is defining invalid
   transitions, ownership, stable EOS, and cleanup under early or failed execution.
2. Eager validation prevents partial output followed by a late schema or predicate failure and gives
   callers a useful exception category.
3. A limit-zero result alone cannot prove correct behavior. A counting child is needed to observe that
   no hidden upstream pull occurred.
4. Defensive snapshots trade memory for reproducibility and local ownership. That is appropriate for
   this bounded in-memory unit but should become streaming page ownership in a disk-backed unit.
5. A captured log is provenance, not proof of success. The current log proves a missing toolchain and
   exit status 127; it does not prove compilation or correct execution.

## Next bounded step

On a machine with JDK 8 or newer, run the exact block in `RUN.md`, inspect the compiler diagnostics or
the final test `SUMMARY`, and preserve the regenerated `test-output.txt`. Do not promote the validation
label without a controlled evaluator result.
