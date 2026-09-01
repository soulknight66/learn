# Review: validate while running

Inspect `review.py`. The author argues that every opcode is checked before use, so a separate validation
pass would only duplicate work. Review that claim against the observable-output and control-flow
requirements. Include a binary-shaped counterexample, not only prose.
