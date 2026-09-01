# Comprehension Prompts

Answer each prompt in your own words after completing the project. Use evidence from your implementation, tests, and experiment. Keep each response focused; source or test references are more useful than long quotations.

1. State the bracket invariant your loop maintains. Point to the update logic and to tests that would fail if either branch broke it.

2. Why can mathematically equivalent midpoint expressions behave differently in floating-point arithmetic? Describe how you tested the observable promise made by your implementation, without claiming that a few examples prove universal safety.

3. Give one case in which a small interval width is useful but a small residual is not established, and one case in which a small residual alone gives weak location information. How does your API keep the two observations distinct?

4. Explain the scale term in your mixed absolute/relative stopping rule. What happens near zero, and which test makes that choice visible?

5. What does floating-point stagnation mean in your loop? Explain why raising `maxiter` alone cannot resolve the adjacent-endpoint case.

6. Trace the function-evaluation count for an ordinary non-endpoint iteration and for an endpoint-root return. Cite the instrumented test that checks your stated contract.

7. Pick one invalid-input outcome and one numerical-runtime outcome. Why did you represent them as you did, and how could a caller distinguish and recover from each without parsing message text?

8. Choose one large-magnitude test. Identify the intermediate operation that a less careful implementation could overflow and explain exactly what property your assertion checks.

9. Compare your `Float32` and `Float64` evidence. Which assertions had to be type- or scale-aware, and which contract properties should remain type-independent?

10. Name the strongest correctness claim justified by your current evidence, then list two important claims it does not justify. Include at least one limitation concerning the mathematical assumptions on `f`.
