# Comprehension prompts

Answer these in `submission/RESPONSES.md`. Use your own reasoning and refer to your implementation or tests where requested. There is no answer key in the learner materials.

1. Follow one example through your API. Which shape and value invariants must hold before calculation, and where does your implementation enforce each invariant?
2. Why can a mathematically correct probability-space expression for binary cross-entropy fail at a large-magnitude logit? Explain the strategy your code uses without merely restating a function name.
3. What consistency error arises if batch loss is averaged but its gradient is summed? Name a test that would detect it.
4. Explain why comparing an analytic gradient with a central finite difference is stronger than testing only that loss decreases after one update. What can still make the numerical comparison misleading?
5. A reviewer notices `sum(a * b for a, b in zip(weights, features))`. Describe the failure that can be hidden here and the contract/test that prevents it in your module.
6. Give the time and auxiliary-space complexity of your batch loss-and-gradient calculation in terms of batch size \(n\) and feature count \(d\). Tie each term to work or storage in your implementation.
7. Distinguish a catalog link, locally available learning content, and a validated course unit. Why does finishing this kickoff establish none of the claims associated with finishing the approximately 80-hour catalog course?
8. Identify one result recorded in `EVIDENCE.md` that an examiner can reproduce deterministically, and one engineering-quality claim that still requires inspection rather than trusting the record.

