# Comprehension questions

Preparation label: **questions only; no answer key is included in learner-safe material**.

Answer all questions in `submission/COMPREHENSION_RESPONSES.md`. Show reasoning where a calculation or test design is requested. Use your own words, and distinguish facts you derived from observations you measured.

1. Let `x = FiniteSignal(-1, (2, -1, 3))` and `h = FiniteSignal(2, (4, 5))`. Derive the start index, stored length, and every stored sample of their linear convolution. Explain how the nonzero starts affect indices but not tuple positions used during accumulation.

2. For an arbitrary nonempty `x`, describe both the stored representation and the index equation for `x.shift(3)`. Which direction does the visible signal move on an integer time axis? Explain why a shift implementation that changes sample order would violate the contract.

3. Contrast an empty signal with `FiniteSignal(-2, (0.0, 0.0, 0.0))`. What observable behaviors must remain different, and why can automatically trimming boundary zeros break the specified API?

4. Suppose both convolution implementations agree on 10,000 generated inputs. Why is that not a proof of correctness? Name one plausible correlated defect and design one independent check likely to reveal it.

5. Design a deterministic test of the relationship between input shifts and convolution. State the relationship you expect, include shifts of both operands, and ensure the case would fail for a sign error in `shift`.

6. Mathematically, convolution is commutative. Explain why two floating-point result tuples might nevertheless differ in their least significant bits. State when exact equality is appropriate in this unit and when a tolerance-based comparison is better.

7. Give time and auxiliary-space bounds for each implementation using represented lengths `N` and `M` and nonzero counts `Kx` and `Kh`. Include the cost of satisfying the required full-length output contract; do not discuss only multiplication counts.

8. A benchmark shows the sparse version faster on one zero-heavy input and slower on one dense input. What may you conclude? Identify at least four factors that limit generalization or threaten measurement validity, and propose one follow-up experiment.

9. Choose three validation or immutability requirements from the task. For each, describe a realistic downstream defect that could occur if it were omitted. At least one example must involve Python's type system or numeric edge cases.

10. The catalog has a normalized “Course Website” record and an “Assignments” record whose source metadata marks it as official. Explain why neither record was automatically made a study unit in this kickoff graph. What additional evidence is needed, and what is the strongest completion claim possible after this unit is independently validated?
