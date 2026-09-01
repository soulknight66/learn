# Comprehension prompts

Answer these in `submission/COMPREHENSION_RESPONSES.md`. These are reasoning prompts, so support each answer with concrete details from your implementation. There is no need to use or retrieve external course material.

1. For your exact implementation, derive the worst-case running time of `fit` and of predicting `q` queries from `n` training vectors of dimension `d`. Include the effect of how you select or sort `k` neighbors. State the additional space used and distinguish stored model state from temporary prediction space.

2. The contract uses original training index, aggregate neighbor distance, and lexical label order as tie breakers. Explain why specifying all three matters for reproducibility. Give one plausible refactor that could silently make results nondeterministic or change them while still appearing mathematically reasonable.

3. Why does `fit` copy validated training data? Describe a failure that could occur if it retained caller-owned nested lists. What performance or memory tradeoff does this defensive boundary create?

4. Suppose a later experiment tries several values of `k` and reports the best result on the same held-out examples used to choose `k`. Explain what is wrong with that procedure. Propose train, validation, and test responsibilities that preserve a trustworthy final estimate.

5. Flattening an image lets this implementation treat it as a vector but discards explicit spatial structure. Identify one consequence for the distance measure. Then explain which public boundary you would preserve so that a later spatially aware classifier could replace k-NN with minimal changes elsewhere.

6. Imagine `n` grows until brute-force prediction no longer meets a latency target. Propose one exact optimization or alternative search strategy. State which semantics might change, which contract semantics must remain stable, and which existing tests you would retain or revise.
