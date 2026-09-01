# Comprehension Prompts

Answer each prompt in your own words in `responses.md`. Refer to specific files, tests, or observed behavior from your implementation where requested. Do not paste generic definitions.

1. A topological-sort function can be correct while the service containing it is unsafe or unusable. Identify three service-level obligations beyond the algorithm itself, and point to evidence for each in your work.

2. Choose one acceptance scenario you wrote before implementation. Explain how it differs from a unit test of the planner and how the two forms of evidence complement each other.

3. Why is lexicographic tie-breaking part of the public contract rather than merely an implementation detail? Describe one maintenance or operational problem that nondeterministic valid orders could cause.

4. Compare these failures: malformed JSON, a dependency naming an unknown task, and a cycle among known tasks. Explain why the service classifies them as it does and what a client can do after each response.

5. Select one required edge case. Trace it from the HTTP request boundary through the planner or validator to the response, naming the test that would detect a regression.

6. What does `GET /health` establish, and what does it fail to establish? Give one additional production-readiness signal that would matter if this slice were deployed later.

7. Name one feature you deliberately deferred. Explain how the timebox and user story informed that decision, and identify the first contract question you would resolve before adding it.

8. What conclusions can an examiner legitimately draw from passing tests and completing this unit? What claims about CS169 or production readiness would still be unsupported, and what further evidence would be needed?
