# Comprehension prompts

> Artifact provenance: course-manager-authored for `managed_unit_01_lambda_evaluator`.  
> Validation label: `LEARNER_SAFE_PREPARED`; responses have not been validated.

Write concise responses in `submission/COMPREHENSION_RESPONSES.md`. Refer to the behavior of your implementation where requested.

1. Compute the free-variable set of `λx. ((x y) (λy. x z))`. Explain each removal and union rather than giving only a set.

2. Consider `[x ↦ y](λy. x y)`. Explain why naive structural replacement changes binding, and derive a capture-avoiding result under your documented fresh-name policy.

3. Give two terms that are alpha-equivalent despite nested shadowing. Then change exactly one occurrence so that the pair is not alpha-equivalent, and explain which binding relationship changed.

4. Trace the small steps of `((λf. λx. f x) (λz. z)) (λw. w)` under the unit's evaluation strategy. For each transition, identify the applicable rule and the fuel consumed.

5. Give one term that is stuck and one term that requires more reductions than a chosen fuel budget. Explain why reporting both as the same outcome would make debugging and testing weaker.

6. State the complete avoid set used when your substitution code chooses a fresh binder. What failure could occur if one of its categories were omitted?

7. Describe how your alpha-equivalence algorithm distinguishes a renamed bound occurrence from a free occurrence with the same spelling. Include one test that would fail under literal tree equality.

8. Identify one place where two individually plausible components could disagree at their interface. Explain the test you use to expose that disagreement and what evidence would make the diagnosis reproducible.
