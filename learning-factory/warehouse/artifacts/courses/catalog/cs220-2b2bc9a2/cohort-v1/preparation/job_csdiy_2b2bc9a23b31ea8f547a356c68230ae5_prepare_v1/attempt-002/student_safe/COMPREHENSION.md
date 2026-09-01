# Comprehension Prompts

Write your responses in `COMPREHENSION_RESPONSE.md`. Number them 1–8. Explain in your own words; short code excerpts from your own implementation are welcome when they sharpen the explanation.

1. The public function borrows an input `&str` but returns owned `String` values. Explain why that boundary is useful for callers. Identify what would have to change if the returned task names borrowed directly from the input.

2. Without running the program, determine the exact successful output order for this input. Show the ready set after each selection and connect every tie decision to the contract.

   ```text
   compile -> test
   lint -> test
   fetch -> compile
   docs
   ```

3. Consider the line `alpha -> beta -> release` on line 7. Describe the error information the library should return, where the line number originates, and why this is an expected error rather than a reason to panic.

4. State the graph invariant your implementation maintains when it sees the same edge twice. Explain one bug that could occur in topological planning if adjacency and indegree accounting treated duplicates inconsistently.

5. For `a -> b`, `b -> a`, and `b -> c`, explain what belongs in the reported unscheduled list. Why is “unscheduled” a more accurate contract term than asserting that every reported task is part of a cycle?

6. Choose one parser behavior and one CLI behavior. For each, explain the most appropriate test boundary, the observable assertion, and what regression the test protects against.

7. Give the asymptotic time and space costs of your implementation in terms of tasks `V` and distinct edges `E`. Account explicitly for the ordered structure used to select the next task, rather than quoting only the textbook topological-sort bound.

8. Point to one ownership, error, or module-boundary decision in your implementation that makes future change safer. Name a plausible change and explain how the decision localizes or fails to localize it.

These prompts concern the kickoff project only. They do not certify mastery of the rest of CS220.
