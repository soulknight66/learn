# Comprehension Check

Provenance: Course-manager-authored for `managed_unit_001_linear_regression_engineering`; no external course content was retrieved.  
Validation label: `AWAITING_HARNESS_VALIDATION`

Answer all questions in `COMPREHENSION_RESPONSES.md`. Refer to your own implementation and test names where requested. Do not paste code except for a single expression when a question explicitly asks for one.

1. Starting from the stated least-squares objective, write the vectorized gradient with respect to the feature coefficients. Give the shape of every factor and of the result.

2. Explain what changes in the gradient calculation when an intercept is fitted separately. Why should the public `coef_` not include that intercept?

3. Give one observed symptom of a learning rate that is too large and one symptom of a learning rate that is unnecessarily small. Identify which recorded evidence from your implementation would support each diagnosis.

4. Why is a `numpy.linalg.lstsq` result useful in the tests but inappropriate inside the required `fit` implementation? Explain how that separation reduces the chance of a false-positive test.

5. State the per-update time and auxiliary-space complexity of your implementation in terms of samples \(m\) and features \(n\). Tie the result to the operations your code actually performs.

6. Name the tests that establish non-mutation and deterministic repeat fitting. For each, describe precisely what observable failure it would catch.

7. Suppose `fit` succeeds and a later call to `fit` receives a target containing NaN. Describe the model state your contract promises after the exception, and explain one implementation strategy that preserves that contract.

8. Your optimization loss becomes finite and nearly constant, but the predictions disagree materially with the independent reference. Give two distinct hypotheses—one about optimization and one about implementation—and one deterministic check for each.

These questions assess reasoning about your submitted work. They do not establish completion of any later course unit.
