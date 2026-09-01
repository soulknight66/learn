# Comprehension prompts

Answer all prompts in `submission/COMPREHENSION_RESPONSES.md`. Use your own implementation and reasoning. Give concise but explicit explanations; code fragments are optional unless requested.

1. A mapping contains `{"build": ["test"]}` and no `"test"` key. What vertex set must the public contract recognize, and what kind of implementation mistake could silently violate that contract?

2. Explain why treating repeated adjacency entries as separate edges can make the maintained state misleading. Identify where your implementation establishes the edge-set interpretation.

3. Two algorithms can both return valid topological orders for the same graph. What additional guarantee does this unit require, and why can that guarantee matter in build systems, tests, logs, or generated artifacts?

4. State the central invariant used by your implementation in mathematical or precise prose. Explain separately how initialization establishes it and how one scheduling step preserves it.

5. Why does “no eligible vertex remains” have different meanings depending on whether all vertices have already been emitted? Connect your explanation to the exception's `nodes` attribute.

6. Describe one example-based test, one property-oriented test over a family of graphs, and one metamorphic test in your suite. For each, name a plausible defect it can expose that another of the three might miss.

7. Suppose a caller provides adjacency values as generators with visible side effects. Which behavior is guaranteed by the contract, which behavior is deliberately outside it, and what design change would you consider before exposing this API in a larger production system?

8. Your implementation meets its target asymptotic complexity, but a teammate proposes sorting every adjacency list for readability. Analyze whether that changes correctness, determinism, or the complexity argument, and state how you would decide whether to accept the change.
