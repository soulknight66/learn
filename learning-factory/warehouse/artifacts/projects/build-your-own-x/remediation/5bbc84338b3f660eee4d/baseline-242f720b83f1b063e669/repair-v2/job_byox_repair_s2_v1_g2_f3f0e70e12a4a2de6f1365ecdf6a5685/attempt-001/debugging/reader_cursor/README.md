# Debugging: escaped-string cursor

`buggy_scanner.py` is a reduced scanner used only for this exercise. An invalid escape after a valid
escape reports a column one position too small.

1. Construct the shortest input that demonstrates the drift.
2. Identify the state update whose units disagree with the consumed input.
3. Propose a regression assertion for both the token value and the later error location.

Do not replace location tracking with a rescan; preserve one forward pass.
