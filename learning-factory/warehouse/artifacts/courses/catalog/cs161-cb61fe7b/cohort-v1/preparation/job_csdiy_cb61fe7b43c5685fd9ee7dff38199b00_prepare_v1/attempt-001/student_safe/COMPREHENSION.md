# Comprehension Prompts

Respond to each prompt in `submission/COMPREHENSION.md`. Use precise reasoning tied to your implementation; include a small state trace or test reference where useful.

1. Why must the caller principal come from a trusted adapter? What security claim would fail if an untrusted client could choose that value?
2. Give two request histories that should be indistinguishable through the public error API: one involving an existing but inaccessible document and one involving an unknown identifier. What leakage does this prevent, and what leakage remains in scope?
3. Trace how a retained input slice or a returned output slice could bypass authorization without defensive copies. Which tests demonstrate that your store owns its representation?
4. Identify the linearization point of `RevokeRead`. Explain why a read that begins after revocation returns cannot succeed, and describe what your policy permits for an overlapping read.
5. Why does an unpredictable document identifier not replace authorization? Conversely, what abuse becomes easier if identifiers are sequential even when authorization checks are correct?
6. Describe how your controlled identifier source forces a collision. Which invariant would an overwrite-on-collision bug violate?
7. Choose one denied mutation and show, field by field, how a test establishes that no partial state change occurred.
8. Name two properties a networked, persistent version would need that this unit does not provide. For each, identify the new trust boundary that would have to enter the threat model.
