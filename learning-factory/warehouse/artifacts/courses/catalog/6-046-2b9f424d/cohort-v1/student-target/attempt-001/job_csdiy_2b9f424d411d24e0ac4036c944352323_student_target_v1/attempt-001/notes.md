# Kickoff unit working notes

## Scope

This work covers only the bounded **Algorithm-to-Component Kickoff: Weighted
Interval Scheduling** unit. It does not establish completion of MIT 6.046 or of
any broader course material.

## Contract restatement

Preconditions for a valid call:

- The outer object is a finite `Sequence`.
- Each item is a `Job`; IDs are unique, nonempty strings.
- Times and values are integers but not booleans; `start < finish` and
  `value >= 0`.

Postconditions:

- Return job IDs, in ascending `(finish, start, job_id)` order, for a compatible
  maximum-total-value subset.
- Treat intervals as half-open, so `earlier.finish <= later.start` is compatible.
- Among equal-value subsets, compare selection bits from greatest canonical
  index down and prefer `0` at the first difference.
- Do not mutate the sequence or its jobs. Validate before optimization.

Failure behavior is `TypeError` only when the outer object is not a sequence;
all invalid records or fields use `ValueError`.

## Hand-worked cases

1. `A=[0,2), value 5`, `B=[2,4), value 5`, `C=[0,4), value 10`.
   Canonical order is `A,C,B`. The tied schedules are `{A,B}` with reverse bits
   `101` and `{C}` with reverse bits `010`; therefore `{C}` is required.
2. `P=[0,3), value 8`, `Q=[3,5), value 4`, `R=[0,5), value 12`.
   Canonical order is `P,R,Q`. `{P,Q}` and `{R}` both total 12; their reverse
   bits are `101` and `010`, so `{R}` is required.
3. Three compatible zero-value jobs tie with the empty set. At the greatest
   selected index the empty set has `0`, so all zero-value jobs are omitted.
4. `long=[0,10), value 10` loses to two touching jobs `[0,5), value 6` and
   `[5,10), value 6`; a locally highest-value choice is not sufficient.

## Implementation hypothesis and invariants

Hypothesis: ordinary weighted-interval prefix dynamic programming needs only a
strict comparison for inclusion. For prefix `1..i`, compare
`value(i) + best[p(i)]` with `best[i-1]`. Include only when strictly greater;
on equality, exclude `i`. Because `i` is the greatest index in that prefix,
this equality choice is exactly the reverse-bit rule. The predecessor state is
already canonical by induction.

State invariant: `best[i]` is the maximum value attainable from the first `i`
canonical jobs, and its recorded decisions reconstruct the unique preferred
subset among schedules with that value. `p(i)` is the number of earlier jobs
whose prefix can precede job `i`, found using `finish <= start`.

Planned falsification experiment: compare the production result—not merely its
value—with an independent oracle that enumerates every subset on at least 200
fixed-seed instances of at most 10 jobs. Direct permutation and zero-value cases
separately target the tie hypothesis.

