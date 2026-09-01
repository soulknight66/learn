# Comprehension Questions

Answer these in `COMPREHENSION_RESPONSES.md` after completing the implementation. Show reasoning, units or array shapes where relevant, and refer to concrete code or experiment evidence. There are no answers in this packet.

1. Starting from the stated mean-squared-error objective, derive the batch gradients for the weights and intercept. Annotate every intermediate expression with its shape.

2. For \(n\) samples, \(d\) features, and \(k\) executed gradient steps, what are the training time and auxiliary-space costs of your implementation? Identify any stored history that changes the space bound.

3. Why can differently scaled feature columns make one fixed learning rate difficult to use? Connect your explanation to the geometry of the objective and to evidence from your deterministic experiment.

4. State your exact convergence rule. Give one situation in which it can stop too early and one in which it can run to `max_steps` even though the model is useful.

5. Explain how your tests distinguish a correct optimizer from an implementation that merely returns predictions with low error on one data set. Name the independent oracle or invariant used by each relevant test.

6. What state must be learned during `fit`, and what input facts must be checked again during `predict`? Explain why the distinction matters for a reusable component.

7. Compare batch gradient descent with solving ordinary least squares directly. Discuss at least numerical behavior, computational cost, and when each approach is attractive; do not reduce the answer to a single big-O expression.

8. Suppose training loss is small but held-out error is much larger. Give three distinct hypotheses and one controlled check for each. Do not use the held-out set to tune the model in your proposed checks.
