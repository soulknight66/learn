# Comprehension Questions

Artifact provenance: manager-authored for the local reproducible-data-audit kickoff.

Validation label: `QUESTION_SET_UNVALIDATED` — this file contains questions only; it is not an answer key or completion record.

Answer each question in your own `COMPREHENSION_RESPONSES.md`. Refer to concrete behavior in your implementation where useful.

1. Why does the contract treat an empty `score` differently from a nonempty score token that cannot be parsed? What downstream mistake could occur if both cases were represented only as `null` with no error metadata?

2. Why are duplicate identifiers reported at dataset level while all duplicate rows are preserved? Describe one unsafe alternative and the information it could destroy.

3. Name at least four sources of nondeterministic or machine-specific output that the implementation must exclude or control. Explain how byte-identical output helps review and debugging.

4. Give one property-based statement about city normalization that could be tested across many generated strings, even though this unit uses only `unittest` and a small fixed fixture.

5. Analyze the worst-case running time and auxiliary-space use in terms of the number of records and the total number of input characters. Identify which required output prevents a streaming implementation from using constant total space.

6. State two invariants that should hold between parsed records, row validity, summary counts, and field statistics. Where in your design are those invariants established or checked?

7. What does the input SHA-256 establish about provenance, and what does it not establish about the quality, truth, or safety of the data?

8. Suppose a later job discovers an assignment link on the course website. What evidence must be recorded before that link can be represented as available material or ordered as an official unit? Why is discovery alone insufficient?
