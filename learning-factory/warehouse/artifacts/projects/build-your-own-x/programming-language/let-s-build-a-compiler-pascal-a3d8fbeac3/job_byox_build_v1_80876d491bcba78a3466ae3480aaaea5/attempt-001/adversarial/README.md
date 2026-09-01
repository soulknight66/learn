# Adversarial evaluation boundary

Adversarial cases are evaluator material, not part of the learner view. The
sealed corpus targets token boundaries, nesting, static name resolution,
arithmetic limits, nontermination, and output-before-error behavior.

No fuzzing was run on the generation host. Corpus presence is not a `FUZZED`
label. See `sealed/adversarial/` for the harness-owned cases and expectations.
