# Comprehension Prompts

Answer these in `COMPREHENSION_RESPONSES.md` after completing the implementation. Use concise reasoning, and cite your source or test locations where the implementation is relevant. Do not rely on external course material.

1. Which graph properties belong at the construction boundary, and what later code becomes simpler because those properties are enforced once?

2. Compare adjacency sets with permanently sorted adjacency tuples. Discuss construction, neighbor lookup or iteration, memory, deterministic output, and what your implementation chose.

3. Why must reversed duplicate edges be normalized before degree and mean aggregation are computed? Describe a failure that would occur if they were silently counted twice.

4. For an isolated node, derive the message-step expression that follows from the specified zero neighbor mean. Explain why the chosen convention needs an explicit test.

5. Give tight asymptotic time and auxiliary-space bounds for your BFS on the reachable subgraph. State which representation assumptions your bounds use.

6. Explain why the specified message step should be equivariant to a bijective renaming of node identifiers. Name two plausible implementation mistakes that a permutation test could expose.

7. Separate topology validation from feature and parameter validation. Where does each occur in your code, and what bug or ambiguity does that placement prevent?

8. Select one invalid-input test and one algebraic-property test from your suite. For each, explain what defect it can catch that an ordinary happy-path example may miss.

9. Give two different neighbor-feature multisets that a coordinate-wise mean aggregator cannot distinguish. What graph information is lost, and what bounded future change could preserve more of it?

10. If this package had to process a graph too large for the current representation, what is the first representation or API boundary you would revisit? Defend one change and one tradeoff without implementing it.

These responses are evidence for this kickoff only; they are not a claim of whole-course completion.
