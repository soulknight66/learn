# Comprehension prompts

*Artifact provenance: course-manager-authored for the bounded kickoff. Validation label: `LEARNER_SAFE_KICKOFF_PREPARED_NOT_VALIDATED`.*

Answer these in `COMPREHENSION_RESPONSES.md`. Use your own implementation and evidence; concise diagrams or pseudocode are welcome, but do not paste generic definitions without applying them.

1. Immediately after a successful push that caused growth, draw or describe the relevant stack object, heap allocation, pointer, length, and capacity. Which facts would become false if the vector retained the old pointer after the old allocation ceased to be valid?

2. Choose two public-boundary invariants from this unit. For each, identify one operation most likely to break it and explain how your implementation re-establishes or preserves it before returning.

3. Consider a request for a capacity so large that converting the element count to a byte count cannot be represented safely. Explain why checking only after allocation is too late. Point to the check and test evidence in your submission.

4. Describe the required state of the vector when a growth allocation fails. Explain how the structure of your implementation preserves that state; distinguish the pointer variable used while attempting growth from the vector's owning pointer.

5. Give worst-case and amortized time bounds for push, and worst-case bounds for indexed get, insert, and remove in your implementation. Tie each nonconstant bound to the elements or bytes actually moved.

6. Select one out-of-bounds operation from your tests. Trace control flow from the public call to its return and list every observable piece of vector state that must remain unchanged.

7. From your GDB evidence, explain the defect, the observation that separated its root cause from its symptom, and why the final change fixes it. Name one additional test that would prevent regression.

8. Compiler warnings, functional tests, GDB, and a dynamic memory checker provide different evidence. State one defect class each is particularly useful for finding and one limitation of relying on any one of them alone.

9. Suppose a caller copies an `IntVec` with plain structure assignment and later destroys both copies. Analyze the ownership problem. Propose an API-level design that permits either an independent copy or an explicit ownership transfer without ambiguity.

10. Review your Git history as if it were a teammate's change. Identify one commit boundary that improves reviewability and one remaining risk or follow-up that a reviewer should request before this component were used in production.
