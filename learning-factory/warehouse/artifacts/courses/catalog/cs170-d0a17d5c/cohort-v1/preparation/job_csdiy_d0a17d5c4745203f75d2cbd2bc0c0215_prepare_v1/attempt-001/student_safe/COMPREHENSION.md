# Comprehension check

Complete this after the implementation, tests, and benchmark. Put your responses in `COMPREHENSION_RESPONSES.md`; do not edit this question file. Refer to specific functions, tests, and evidence in your own submission. Aim for concise reasoning rather than definitions copied from a source.

1. Your input contains repeated values. Explain precisely which index pairs count as inversions and why your implementation cannot accidentally count an equal-valued pair.

2. State an invariant for the operation that combines two solved subproblems. Identify when it holds, how one step preserves it, and what it establishes at termination.

3. Partition all possible inversions of a nontrivial input into exhaustive, disjoint categories. Explain where your implementation counts each category and why none can be counted twice.

4. Give the worst-case running-time recurrence for your implementation, including the nonrecursive term. Solve it and relate each term to concrete work in the code. Separately account for peak auxiliary space.

5. What observable bug could input mutation cause for a caller even if the returned count is correct? Point to the test that would detect mutation and explain why checking value equality alone may be insufficient for the returned list.

6. Describe the domain on which your quadratic oracle is trustworthy and useful. Why should that oracle remain in the test code, and what kinds of defect could make agreement between the oracle and production implementation misleading?

7. Select two adjacent benchmark sizes. Interpret their timing relationship in light of the proved bound, then give at least two plausible sources of measurement noise or bias. Explain why the data alone cannot establish the asymptotic result.

8. Trace one invalid command-line input from standard input to process exit. Explain how your design keeps machine-readable standard output separate from diagnostics, and identify the subprocess assertions that preserve this contract.

9. Suppose this module becomes part of a long-running service. Name one reliability risk not addressed by the bounded task, and outline a focused next experiment or change without implementing it now.
