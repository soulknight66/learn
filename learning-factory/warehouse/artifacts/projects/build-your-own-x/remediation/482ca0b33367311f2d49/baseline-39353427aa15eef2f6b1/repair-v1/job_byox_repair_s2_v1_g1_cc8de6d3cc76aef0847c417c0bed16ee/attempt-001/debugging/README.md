# Debugging exercise: the sibling-prefix escape

Instructor-gated prompt; no answer is stored here.

A learner implementation computes `candidate = root / member_name` and accepts it when
`str(candidate.resolve()).startswith(str(root.resolve()))`. A test using `../root-backup/report`
unexpectedly writes outside `root`, while ordinary `../../etc` cases are rejected elsewhere.

Reproduce the bug entirely in a temporary directory, explain why the condition returns true, and add
a regression that distinguishes path components rather than string spelling. Also consider what
happens when an existing parent inside `root` is a symbolic link. Do not use real system paths.

The evaluator answer for this exercise is under `sealed/debugging/layer_escape/`.
