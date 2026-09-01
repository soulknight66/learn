# Comprehension questions

Write numbered responses in `submission/COMPREHENSION_RESPONSES.md`. Use your own reasoning and refer to concrete choices in your implementation where requested. These prompts ask for explanation, not copied definitions.

1. Which elementary row operations preserve the solution set of `A x = b`, and why does that property matter to the solver?

2. Describe the invariant after the first `k` pivot positions have been processed. How does that invariant support termination and back substitution?

3. Why can selecting a larger available pivot reduce numerical trouble? What important guarantee does partial pivoting still not provide?

4. For a singular square system, what observable reduced-row patterns distinguish no solution from more than one solution? Relate this to your two public exceptions.

5. Why is one fixed absolute zero threshold inappropriate for both very small and very large coefficient scales? Explain how your default policy responds to scale.

6. A solver returns `x` with a small residual `||A x - b||`. What does that establish, and what does it fail to establish about the error in `x`?

7. Explain one way in-place row operations could violate the public mutation contract. How does a test demonstrate the absence of that defect?

8. Tests for numerical code need an oracle. Identify the oracles used by two of your tests and one way each oracle could be misleading if chosen carelessly.

9. Derive the solver's dominant time complexity and auxiliary-space complexity. Separate storage newly allocated by your implementation from caller-owned input storage.

10. Name two capabilities or safeguards a production numerical linear algebra library should have beyond this unit's component. For each, connect the capability to a specific risk.

11. Consider a test that passes before you deliberately replace the pivot-selection comparison with a wrong one. What would that reveal about the test, and how would you strengthen it?

12. Which design decision in your implementation was least determined by the mathematical algorithm itself? Defend it as an interface or engineering choice.
