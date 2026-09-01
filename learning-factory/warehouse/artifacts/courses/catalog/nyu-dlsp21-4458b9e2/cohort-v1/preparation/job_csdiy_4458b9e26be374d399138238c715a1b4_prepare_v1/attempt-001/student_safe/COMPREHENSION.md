# Comprehension prompts

Document status: **LEARNER-SAFE QUESTIONS — NO ANSWER KEY — NOT YET VALIDATED**

Write your answers in `artifacts/comprehension.md`. Number them to match the prompts. Aim for precise reasoning; diagrams or equations are welcome where they clarify an argument. When a prompt refers to your implementation, cite a function or test by name.

1. Show algebraically why adding the same finite constant to every logit leaves the exact softmax distribution unchanged. Then identify the distinct floating-point failures that an implementation can still encounter.

2. Compare computing cross-entropy directly from logits with first materializing a probability and then taking its logarithm. Give a concrete extreme-logit scenario and trace the relevant intermediate values or bounds.

3. For one labeled example, derive the partial derivative of mean cross-entropy with respect to a weight entry and a bias entry. State the shapes of every gradient returned by your implementation and explain where averaging occurs.

4. Analyze the time and auxiliary-space complexity of one full-batch training epoch in terms of `N` examples, `C` classes, and `D` features. Separate storage needed for the model and gradients from avoidable intermediate storage.

5. Your two runs produce byte-identical metrics. What specific nondeterminism has this ruled out in your program, and what claims about portability, numerical reproducibility, or model quality does it *not* justify?

6. Explain why a finite-difference gradient check can detect a defect that a loss-decrease test may miss, and why the reverse can also be true. Name two ways a poorly designed gradient check could agree with an incorrect analytic gradient.

7. Choose one public input contract from your implementation. Describe a plausible downstream failure if that contract were omitted, justify the exception boundary you chose, and propose one test that distinguishes the intended failure from an incidental Python error.

8. The fixture reaches high training accuracy. Explain why this is not evidence of generalization or whole-course mastery. Design the smallest additional evaluation that would answer one new, sharply stated question without changing this unit into a full machine-learning project.

## Boundary and provenance

These prompts assess only `managed_unit_01_engineered_softmax`; they are not reproduced NYU course questions. Catalog source commit: `adce8e13789dc16aa6d1fbe163e9541736defae4`. External retrieval performed: **no**. Validation label: **PREPARED_NOT_VALIDATED**.
