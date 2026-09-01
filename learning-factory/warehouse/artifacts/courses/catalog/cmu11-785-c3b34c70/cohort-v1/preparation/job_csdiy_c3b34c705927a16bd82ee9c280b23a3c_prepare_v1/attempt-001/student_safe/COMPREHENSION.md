# Comprehension Prompts

Answer all prompts in `responses/COMPREHENSION_RESPONSES.md`. Explain reasoning and use tensor shapes where relevant. These are questions only; no answer key is included in the learner package.

1. Starting from mean multiclass negative log likelihood and the stated L2 term, derive the gradient for every trainable tensor. Annotate the shape of each intermediate and explain where division by batch size occurs.

2. Explain how a mathematically correct softmax or log-likelihood implementation can overflow or underflow in floating-point arithmetic. Describe the stable computation used in your code and a test that would fail for a naive implementation.

3. Describe how your central finite-difference check works. Why must its input avoid ReLU kinks, and why can an excessively small step size make the check less reliable rather than more precise?

4. Choose two invariants at the API boundary besides output shape. For each, identify the defect it is meant to expose and the automated test that provides evidence for it.

5. Suppose a gradient tensor has the expected shape only because NumPy broadcasting silently accepted a mistaken intermediate. Explain how a test could detect this even when one training run appears to reduce the loss.

6. Separate the sources of reproducibility in your experiment into data generation, parameter initialization, update ordering, software environment, and report generation. Which of these are controlled by a seed, and which require another mechanism?

7. Interpret the two learning-rate aggregates without claiming more than six synthetic-data runs support. Name one follow-up experiment that would test a specific alternative explanation for the observed difference.

8. Explain why passing the automated suite is evidence for this implementation but is neither a proof of model correctness nor evidence of completing the full CMU 11-785 course.
