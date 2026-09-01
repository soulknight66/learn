<!--
provenance: Learner-authored record of concrete local hypotheses, commands, observations, corrections, and lessons.
validation_label: SELF_CHECKED_NOT_INDEPENDENTLY_VALIDATED
-->

# Debugging log

This is a concise experiment record, not private chain-of-thought. It covers only the bounded kickoff unit.

## 1. Priority finiteness and arbitrary-size integers

**Hypothesis:** Calling `math.isfinite` uniformly on accepted numeric types may mishandle a valid, arbitrarily large Python integer.

**Experiment:** `python3 -c 'import math; value = 10**1000; print(type(value).__name__, len(str(value))); print(math.isfinite(value))'`

**Observed failure:** The command printed `int 1001`, then raised `OverflowError: int too large to convert to float`.

**Change:** Check exact type first and call `math.isfinite` only for `float`; every Python `int` is already finite. Added `test_arbitrarily_large_integer_priority_is_accepted`.

**Lesson:** Validation conversions can accidentally narrow a contract even when the production operation itself supports the value.

## 2. Documented command versus available interpreter

**Hypothesis:** The initial implementation would run with the prescribed unqualified `python3 -m unittest` command.

**Experiment:** `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_min_priority_queue.py`

**Observed failure:** Import stopped at `from __future__ import annotations` with `SyntaxError: future feature annotations is not defined`. The traceback identified the unqualified interpreter as Python 3.6; the implementation had also used newer built-in generic syntax and `perf_counter_ns`.

**Change:** Replaced version-specific annotations with equivalent `typing.Union`/`Tuple`/`List` forms and used `perf_counter`, while retaining the public behavior. The exact command then passed 9 tests in 0.256 s. A separate CPython 3.11.5 run passed the same 9 tests in 0.177 s.

**Lesson:** Toolchain assumptions are part of reproducibility. Test the literal documented entry point, not only a preferred interpreter.

## 3. Rejected pushes and hidden state

**Hypothesis:** Validating before both append and sequence increment preserves not only immediate observations but later stable ordering.

**Experiment:** For bools, nonnumeric objects, NaN, and both infinities, populate two equal-priority entries, attempt the invalid push, compare `(len, is_empty, peek)`, then add a third equal-priority entry and drain.

**Result:** All subcases raised the specified exception and drained as `first, second, third`. No partial mutation was observed.

**Lesson:** An exception-safety test should probe future behavior capable of exposing mutated private metadata.

## 4. Choosing a child during pop repair

**Hypothesis:** A left-only descent fails when the right child is smaller than both the replacement and left child.

**Experiment:** Use valid pre-pop heap priorities `[1, 3, 2, 4]`. After replacing 1 with 4, the children are 3 and 2. A left-only swap would yield invalid `[3, 4, 2]`.

**Change/evidence:** `_sift_down` compares both child keys before moving. Added `test_pop_selects_the_smaller_right_child`; the next root is 2 and the test passes.

**Lesson:** Repair direction alone is insufficient; the selected descendant must preserve the invariant against both branches.

## 5. Independent model and benchmark

**Hypothesis:** Projected `(priority, sequence)` comparisons remain stable across long interleavings without touching payload ordering.

**Experiment:** Run 2,500 operations from `random.Random(6006)` against a linear-list oracle using payloads whose `__lt__` raises. Compare item identity, priority, root, length, and emptiness after each step.

**Result:** The trace passed. The final seven-trial benchmark also completed without functional errors. Raw timings varied (for example, 16,000-item push trials ranged from 27.087 to 35.496 ms), reinforcing the use of medians and cautious interpretation.

**Lesson:** A reproducible oracle catches state divergence; timing variability is evidence to report, not a correctness threshold.
