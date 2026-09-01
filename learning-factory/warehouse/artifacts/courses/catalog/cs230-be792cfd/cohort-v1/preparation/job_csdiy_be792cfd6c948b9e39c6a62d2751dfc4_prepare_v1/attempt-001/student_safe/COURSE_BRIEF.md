# Course kickoff: reliable deep-learning code

The catalog describes **Coursera: Deep Learning** as an approximately 80-hour course spanning foundational neural networks through later architectures. This package is deliberately smaller: it is one manager-authored, 6-hour kickoff on turning a foundational calculation into dependable Python.

Completing this unit does **not** complete the catalog course, replace an official Coursera unit, or establish credit for any official assignment. The catalog links were recorded but not fetched. No lecture, transcript, textbook, or official assignment is bundled here, and none is required for this unit.

## Why this unit

Strong algorithmic reasoning transfers to software engineering only when assumptions become executable contracts. A mathematically plausible implementation can still fail because of numeric overflow, mismatched dimensions, silent truncation, mutable inputs, weak tests, or irreproducible evidence. This unit uses binary logistic loss—the smallest useful neural computation—to practice those engineering boundaries without hiding them behind a framework.

## Learning outcomes

By the end of the kickoff, you should be able to:

- translate mathematical notation into an explicit Python API and input contract;
- compute logits, probabilities, mean binary loss, and analytic gradients robustly;
- make dimension, label, empty-batch, and non-finite-value behavior deliberate;
- verify derivatives with an independent numerical method;
- build deterministic tests that distinguish examples from edge cases;
- explain running time, extra space, failure modes, and reproducibility evidence.

## Compact concept guide

For features \(x\), weights \(w\), and bias \(b\), a binary linear model first computes the logit

\[
z = w \cdot x + b.
\]

The sigmoid maps that logit to a value between zero and one:

\[
\sigma(z) = \frac{1}{1 + e^{-z}}.
\]

Binary cross-entropy measures disagreement with a target \(y\) in \(\{0,1\}\). Directly composing logarithms with a naively computed probability is fragile at large-magnitude logits. A reliable implementation reasons in logit space, uses numerically stable algebra and standard-library primitives such as `log1p`, and defines behavior for invalid or non-finite inputs. Stability means preserving the intended real-number result as closely as floating-point arithmetic permits; it does not mean clipping away valid information without documenting it.

For a batch, decide whether loss and gradients are sums or means and apply that decision consistently. The unit contract uses the **mean**. An analytic gradient is fast, but a finite-difference approximation provides an implementation-independent check. The approximation itself has limits: its step size must avoid both truncation error and floating-point cancellation.

## Engineering stance

Treat the module as a small library, not a notebook fragment:

- public behavior is explicit;
- invalid inputs fail predictably rather than being silently accepted;
- functions do not mutate caller-owned data;
- tests contain meaningful assertions and run without network access;
- evidence identifies the environment and exact command used;
- self-reported success is not a substitute for an examiner running the work.

No third-party package is needed. Read [STUDY_TASK.md](STUDY_TASK.md) for the build contract and [COMPREHENSION.md](COMPREHENSION.md) for the questions you must answer. No solution key or grading rubric is included in the learner materials.

