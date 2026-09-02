# Debugging exercise index

## Scanner progress

`lexer-progress/` contains a reduced scanner with a deterministic step budget and a failing test. Valid punctuation causes the budget guard to report a stall. Diagnose the violated loop invariant, make the smallest correct repair, and add a regression for every punctuation character.

Do not remove or inflate the step budget. The point is to turn a potential infinite loop into a finite, reproducible failure.
