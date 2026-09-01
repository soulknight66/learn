# Sealed design record

## Pipeline ownership

The reference makes every public stage independently defensive. `Scan` owns source-byte classification and produces canonical token payloads. Because callers can construct exported `Token` values, `Parse` first validates ordering, spans, lexemes, integer payloads, keyword classification, and the single final EOF. The same rule repeats at later boundaries: normal upstream output is valid, but public downstream entry points do not assume callers used the upstream function.

`Build` is intentionally thin orchestration. `Execute` goes through `Build` and `Run`, so it cannot conceal a broken compiler by directly evaluating the AST.

## Parser cursor

The parser validates that a final EOF exists before constructing a cursor. Therefore `current` is safe, and `advance` never walks past the final element. One-token lookahead distinguishes top-level `(let ...)` and `(print ...)` from a binary expression without speculative consumption. Expression parsing consumes an opening parenthesis, verifies an operator, recursively consumes exactly two operands, then requires a closing parenthesis.

Composite spans join the opening delimiter's start to the closing delimiter's exclusive end. An error uses the current token's start; at truncation this is the positioned EOF.

## Analysis and slots

The analyzer walks the ordered statement slice. For a `let`, it validates and checks the declaration name for duplication when encountered, analyzes the initializer against only earlier bindings, then inserts the new name. This gives the declaration itself priority over later faults in its initializer while preserving the specified self-reference failure.

Slots use `len(slots)` only at insertion time during ordered traversal. The map is never iterated to assign observable data. Compilation calls analysis defensively and compares the supplied result to the expected source-order mapping. It uses the caller's mapping only after exact agreement, so it neither silently repairs a forged analysis nor emits unsafe locals.

## Compiler invariant

Recursive expression compilation has the invariant “starting depth `d`, finish at `d+1`.” A binary expression emits left, right, then operator, yielding a net stack effect of one. Each statement consumes that expression result with store, print, or pop and therefore restores its incoming depth. A final halt observes depth zero.

Instruction spans retain origins: leaves point to leaf expressions, binary operations point to their complete form, and statement effects point to their complete statement. The halt points to the parsed program span.

## Bytecode trust boundary

Validation is a linear abstract interpretation over stack depth and a sparse set of initialized local slots. It rejects negative slot counts, range-checks each `int64` operand before local access, checks every stack read, enforces one-time store and store-before-load, enforces zero operands where none are defined, and accepts exactly one final halt at depth zero. Sparse maps keep a caller-forged enormous `SlotCount` from triggering a proportional allocation. Every instruction span is checked before being used diagnostically.

This language has no jumps, so one pass represents every possible control path. Adding branches would require a worklist over instruction offsets and merging abstract states.

## Runtime arithmetic and transactions

The VM validates before allocating execution state. Stack, sparse locals, and output are call-local. Add/subtract use boundary inequalities. Multiplication handles zero and the `MinInt64 × -1` cases before checking the wrapped product by division. Division distinguishes zero from `MinInt64 / -1`.

Output accumulates privately and is returned only at halt. Any later arithmetic failure returns `nil`, not the partially accumulated slice. A successful no-print execution begins with `make([]int64, 0)` so its result is non-nil.

## Error determinism

Traversal order establishes error precedence. Messages never format maps. Map iteration in compilation can only discover a generic mismatch with the same stage, code, position, and message, so it cannot alter observable results. Stage errors are returned unchanged by pipeline composition.

## Defensive limitations

Positions are verified for positive coordinates, nonnegative offsets, non-reversed endpoints, and feasible byte/line/column movement. For a line-changing gap, `lineDelta + endingColumn - 1` cannot exceed `offsetDelta`; this rejects a one-byte newline gap that claims column 99. AST containment compares positional movement as well as offsets. Without original source text a downstream stage still cannot prove that gap bytes were actually whitespace or comment text, but every geometrically feasible gap can be represented by ignored bytes. Canonical scanner output maintains exact correspondence.

## Validation and disclosure roles

Oracle self-tests import only `example.com/pebble-reference`. Learner acceptance tests instead import `example.com/pebble`; the harness copies their locked source to scratch space and generates the candidate replacement, with network and automatic toolchain lookup disabled. Its self-check requires a temporary module made from the reference to pass the starter invariant, pristine public suite, and sealed suite, then requires three seeded defects to fail the sealed suite.

The learner disclosure policy is strict JSON in `environment/learner-view.json`. `sealed/validation/learner_view.py` copies only its fixed allowlist and rejects symlinks, special entries, unexpected paths, and wrong access modes. `validate_student_view.py` mounts those entries individually in a bubblewrap namespace—only `starter/` writable—and probes both relative sealed paths and the production pack's absolute sealed paths. A deployment that mounts the source pack does not satisfy the policy.
