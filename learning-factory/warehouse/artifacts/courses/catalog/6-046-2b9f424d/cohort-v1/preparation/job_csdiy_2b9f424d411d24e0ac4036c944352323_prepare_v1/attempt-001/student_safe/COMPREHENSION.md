# Kickoff Comprehension Questions

Respond in `submission/COMPREHENSION_RESPONSES.md`, preserving the question numbers. Use your own reasoning and refer to your implementation where requested. These prompts ask for explanations, not copied code; a short paragraph is normally enough unless a proof is requested.

1. Why does the component define jobs as half-open intervals? Give one boundary case whose compatibility would change under closed intervals.

2. State the optimization objective and the deterministic secondary rule separately. Why is “return any optimal schedule” an incomplete software contract for this component?

3. Consider `P = Job("P", 0, 3, 8)`, `Q = Job("Q", 3, 5, 4)`, and `R = Job("R", 0, 5, 12)`. Determine the canonical order, list the maximum-value compatible subsets, and apply the reverse-bit rule to identify the required output.

4. Define the predecessor information needed by an efficient weighted interval scheduling algorithm. Which inequality must its compatibility search use, and how does that inequality follow from the interval convention?

5. State the invariant for each optimization state in your implementation. Then outline an induction showing that the state contains both the best attainable value and the contractually preferred tie result for its prefix.

6. Explain how your reconstruction procedure follows the recorded decisions. What specific bug could occur if optimization uses the prescribed tie rule but reconstruction resolves equal values differently?

7. Give an end-to-end time and auxiliary-space analysis. Identify where sorting, compatibility lookup, optimization, and reconstruction contribute, then explain one qualification caused by Python strings or arbitrary-precision integers.

8. Why should the function validate the complete input before beginning optimization? Discuss both predictable failure behavior and the no-mutation guarantee.

9. How is your exhaustive test oracle independent from the production algorithm? Explain why comparing only total values would fail to check the full contract.

10. Name two useful metamorphic relations for this component. For each, state what should remain unchanged and any preconditions needed for the relation to be valid under the deterministic tie rule.

11. What does a fixed pseudorandom seed contribute to the differential tests, and what does it not establish? Name one carefully constructed case that generated testing could easily miss.

12. Choose one extension—such as mutable jobs, multiple machines, cancellation updates, or a streaming interface—and identify at least two assumptions in the present contract or algorithm that would have to change.

