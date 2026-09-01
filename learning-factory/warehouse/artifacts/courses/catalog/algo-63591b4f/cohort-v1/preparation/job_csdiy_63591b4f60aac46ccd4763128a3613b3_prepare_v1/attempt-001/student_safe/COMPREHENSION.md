# Comprehension prompts

Answer these questions in `submission/COMPREHENSION_RESPONSES.md`. Do not modify this prompt file.

1. State at least four representation invariants for your union-find forest. Use them to explain why `find` terminates and why equality of returned representatives corresponds to connectivity.

2. Start with eight sites and apply these calls in order:

   ```text
   union(0, 1)
   union(2, 3)
   union(4, 5)
   union(6, 7)
   union(0, 2)
   union(4, 6)
   union(2, 4)
   union(1, 7)
   ```

   After each call, give the component count and the partition of sites into components. State which calls return `true`, which return `false`, and the final value of `componentSize(3)`. Do not assume a particular numeric root when tie-breaking is not part of the public contract.

3. Give separate time and space bounds for construction, count queries, `find`, `connected`, `union`, and `componentSize`. Distinguish the worst case for one operation from the amortized bound across a sequence, and explain the roles of weighting and path compression.

4. Suppose path compression changes a node's parent. Should it also transfer or decrement component-size metadata? Explain using the meaning of root-only size metadata and identify when size is actually allowed to change.

5. For `siteCount = 5`, consider the events below:

   ```text
   [0, 1], [1, 2], [3, 4], [2, 3], [0, 4]
   ```

   What should `eventsUntilFullyConnected` return, and why? Then replace the final row with a malformed one-element row. Explain the required behavior even though an earlier prefix may already connect every site.

6. Explain how validating indices before array access and before mutation creates a useful failure boundary. Name one test for each public method that demonstrates this behavior without inspecting private state.

7. Describe your model-based test oracle, case generator, and comparison rule. Why is an oracle built from the same parent-forest logic a weak test? Give one concrete failure that your chosen oracle could expose.

8. Two threads concurrently call `union` and `find` on one instance. Identify at least two state anomalies that can occur without synchronization. Recommend a safe usage boundary or redesign, but do not implement concurrency support for this unit.

9. A product owner asks to add connection deletion while preserving fast online queries. Explain why the current representation and API do not directly support that request. What requirement questions would you ask before choosing a different data structure or an offline strategy?
