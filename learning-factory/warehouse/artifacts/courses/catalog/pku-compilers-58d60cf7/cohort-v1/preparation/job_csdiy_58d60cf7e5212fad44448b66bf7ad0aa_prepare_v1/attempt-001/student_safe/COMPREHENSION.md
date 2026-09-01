# Comprehension Check

Answer these questions after completing the implementation. Refer to concrete types, modules, tests, and observed behavior from your own work. Do not include source code unless a short excerpt is essential to your explanation.

1. Trace one valid input from bytes on disk to bytes in the output file. What invariant is established at each pipeline boundary, and which component owns the integer-range check?

2. Why is recognizing a valid prefix insufficient? Give one malformed input from your test suite that would pass a prefix-only recognizer and explain how your implementation rejects it.

3. What information does your program representation contain? Compare your representation-first design with emitting text during recognition, especially if parenthesized addition were added next.

4. State the invariant that prevents a failed compilation from corrupting an existing output. Describe one automated observation that gives evidence for that invariant and one failure mode the observation would catch.

5. Explain how byte offsets are computed for diagnostics. What happens for a non-ASCII byte, and why is the behavior deterministic across supported environments?

6. Organize your tests into equivalence classes and boundary cases. Which defect class is targeted by the very long integer, and how do you know the implementation does not rely on host overflow behavior?

7. Suppose MiniMain-0 is extended with parenthesized addition in the return position. Identify the grammar, representation, parsing, emission, and test changes you would expect. Name one existing component that should not need semantic changes and justify that boundary.

8. Precisely state what completing this unit demonstrates and three course-level claims it does not support.
