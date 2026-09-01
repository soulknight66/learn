<!--
provenance: Learner-authored from COURSE_BRIEF.md, STUDY_TASK.md, COMPREHENSION.md, and local experiments only.
validation_label: SELF_CHECKED_NOT_INDEPENDENTLY_VALIDATED
-->

# Kickoff unit notes

## Boundary

These notes cover only the manager-authored kickoff unit, **Engineering a Reliable Binary Min-Priority Queue**. They do not claim completion of an official MIT unit or the wider MIT 6.006 course.

## Contract translated into engineering checks

- The public result shape is always `(item, priority)`; representation tuple order must not leak.
- Ordering is by smaller priority and then insertion order. Payload identity is independent of ordering, so an opaque payload must never be compared.
- Valid priorities are exact finite `int`/`float` values, including negatives. `bool` needs an explicit rejection because Python treats it as an `int` subclass.
- Validation must finish before append or sequence allocation. “Unchanged” includes length, root, drain order, and later tie behavior—not merely the backing list.
- Empty `peek`/`pop` raise `IndexError`; repeated `peek` is observationally idempotent.

## Representation lessons

The heap entry `(priority, sequence, payload)` separates the ordering key from the value. The complete invariant is parent `(priority, sequence) <=` each child's key. Sift-up has one possible ancestor path after an append. Sift-down has one possible descendant path after root replacement, but it must compare both children before selecting the next link.

Using a projected two-field key is safer than relying on full Python tuple comparison: unique sequence values guarantee that payload ordering is irrelevant. A “left child first” repair is insufficient; `[1, 3, 2, 4]` is the minimal counterexample after a pop.

## Test and measurement lessons

Example cases establish named boundary behavior. The deterministic list oracle adds long interleavings without duplicating the heap algorithm. Seed 6006 and checks after every one of 2,500 operations make failures replayable and close to their cause.

Timing is observational evidence, not a complexity proof. For 4x input increases, measured total pop medians rose roughly 4.9–5.6x, while push medians rose roughly 4.1–4.4x. This is compatible with the workload and implementation, but host noise and data distribution matter. Worst-case bounds come from the height/invariant argument.

## Production-oriented takeaways

- Verify the actual runtime named by documentation: local `python3` was 3.6.8 even though a 3.11.5 toolchain was also present.
- Avoid converting arbitrary-size integers merely to validate them as finite.
- Tests for rejection should exercise future behavior, not only immediate length.
- A performance script should state seed, sizes, trials, clock, interpreter, raw samples, and medians, and should avoid pass/fail timing thresholds.

Remaining risks are listed in `ENGINEERING_NOTE.md`; independent validation has not yet occurred.
