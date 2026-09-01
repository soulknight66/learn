# Comprehension prompts

Submit reasoned responses in `COMPREHENSION_RESPONSES.md`. This document contains questions only.

1. Prove from the definition of a convex set that the feasible allocations form a convex set. Address both nonnegativity and the budget equality.

2. Which input condition makes the objective strictly convex? Explain what that condition, together with feasibility, says about existence and uniqueness of the optimizer.

3. Explain why \(L=\max_i a_i\) is relevant to the gradient step. What numerical behavior would you watch for if the ratio of largest to smallest weight were very large?

4. The projection routine sorts a temporary vector but the public result preserves input order. Explain both the mathematical purpose of sorting and the software-contract reason for restoring order.

5. Why is a small change in objective value alone an inadequate convergence test? Relate the fixed-point and feasibility residuals to claims the program is allowed to make.

6. What can comparison with a finite-grid oracle reveal, and what can it never prove about arbitrary real-valued inputs?

7. Give one example-based invariant and one metamorphic property from your tests. Describe different defect classes they can expose.

8. Explain how invalid input, iteration exhaustion, and an unexpected internal failure differ. Why should their status, output stream, and exit code not be collapsed into a single “failed” behavior?

9. For the fixed activation charge \(\gamma\sum_i\mathbf{1}[x_i>0]\), determine whether the modified objective remains convex. Justify the conclusion from a definition or a concrete inequality, then state which solver guarantees require re-evaluation.

10. Which output and evidence fields improve reproducibility? Why do those fields, a passing learner test suite, and completion of this lab still not establish independent validation or completion of EE364A?

---

Document provenance: course-manager-authored for `unit_kickoff_trustworthy_convex_allocation_v1` from catalog context only; no external answer source was retrieved.
