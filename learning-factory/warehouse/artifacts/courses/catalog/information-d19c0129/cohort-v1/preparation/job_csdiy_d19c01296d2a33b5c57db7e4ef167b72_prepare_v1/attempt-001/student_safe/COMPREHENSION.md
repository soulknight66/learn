# Comprehension Prompts

> Provenance: manager-authored questions for the bounded kickoff.
>
> Validation label: `LEARNER_SAFE_QUESTIONS_NO_ANSWER_KEY`.

Answer each prompt in `submission/COMPREHENSION_RESPONSES.md`. Show intermediate reasoning where requested. These prompts contain no model answers; write explanations tied to your implementation and tests.

1. For counts `[9, 3, 0, 0]`, form the empirical probabilities, substitute them into the base-2 entropy expression, and report the result to four decimal places with units. Explain how you treated the zero counts.

2. A proposed implementation removes every zero before calculation and then returns `0.0` when nothing remains. Evaluate the two separate decisions: omitting individual zero-count terms and accepting an all-zero input. Relate your answer to the function's public contract.

3. Let every count in a valid count vector be multiplied by the same positive integer. Derive what happens to the empirical probabilities and entropy. Name one test that would detect an incorrect implementation of this property.

4. Why does this task define symbols as bytes rather than decoded text characters? Give a concrete class of input for which text decoding would change behavior or fail, and identify the test evidence you supplied.

5. A streaming implementation passes tests for tiny files but accidentally resets its counters at each chunk. Design a deterministic test that exposes the fault without depending on the implementation's private variables. Explain the expected observable relationship.

6. Describe how your reusable function and CLI distinguish at least three kinds of invalid input. For CLI failures, explain the intended exit status, standard-output content, and standard-error content.

7. Someone claims that a reported value of `0.7` bits per byte guarantees both a compressed file size of exactly `0.7` times the byte count and strong cryptographic unpredictability. Identify the unsupported parts of this claim and the additional assumptions or evidence each conclusion would need.

8. Review the claim that the file analyzer takes linear time and constant auxiliary space as file size grows. Define the variables behind that claim, account for the 256 counters and I/O buffer, and describe evidence that the analyzer does not retain the full file.

Submitting responses is necessary evidence for this unit, but an independent evaluator determines whether they are correct and sufficiently supported.
