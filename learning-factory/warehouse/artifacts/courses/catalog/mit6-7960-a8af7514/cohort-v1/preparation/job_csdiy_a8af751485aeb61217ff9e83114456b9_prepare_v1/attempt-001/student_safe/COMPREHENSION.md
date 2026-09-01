# Comprehension Prompts

Respond in `COMPREHENSION_RESPONSES.md`. Number the responses and cite the relevant function, test, or `run.json` field when the prompt concerns your implementation.

1. Starting from the mean regularized negative log-likelihood, derive the gradients with respect to `W` and `b`. State every intermediate array's shape and explain where the batch-size factor and regularization term enter.

2. Describe the mathematical property that permits a stable softmax calculation. Give one concrete logits row for which a direct exponentiation implementation is unreliable, and explain why the class probabilities should still be well-defined.

3. A gradient checker can report tiny error while both paths contain the same bug. Identify two ways shared code or shared assumptions could cause that false confidence, and explain how your checker reduces those risks.

4. Why use a central finite difference here instead of a forward difference? Discuss both truncation error and floating-point error, including what can go wrong if the step size is made much smaller than `1e-6`.

5. Define what “deterministic” means for this submission. Which sources of variation did you control, which volatile fields did you exclude, and what claim would remain unjustified if the code moved to a different Python/NumPy/platform combination?

6. Suppose every test passes and training loss decreases, but test accuracy is near chance. Give at least three distinct explanations. For each, name one additional observation or test that would help discriminate it from the others.

7. Analyze the time and auxiliary-space complexity of one full-batch loss-and-gradient evaluation in terms of `N`, `D`, and `C`. Identify the dominant stored intermediates and describe one valid memory/time tradeoff for a much larger `N`.

8. Draw an evidence boundary for the finished project: list three claims supported by the tests and experiment, and three broader deep-learning or course-level claims that the project cannot support.

