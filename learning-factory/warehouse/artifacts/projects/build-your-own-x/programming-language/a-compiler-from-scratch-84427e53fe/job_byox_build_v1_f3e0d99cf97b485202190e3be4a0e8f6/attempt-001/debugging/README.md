# Debugging exercises

These prompts deliberately describe symptoms without giving fixes. Keep notes for each exercise before consulting any sealed evaluator material.

## D1: precedence inversion

An implementation prints `12` for `print 2 + 3 * 4;` instead of `14`, while parenthesized input works. Draw the observed AST, identify the parser boundary that consumed too much or too little, and add a regression covering left associativity too.

## D2: negative remainder

Positive division tests pass, but `print -7 % 3;` prints `2`. Determine which host-language behavior leaked through and state an identity that quotient and remainder must satisfy for all sign combinations.

## D3: disappearing outer binding

After an inner block declares `let x`, a later assignment unexpectedly targets that inner slot or reports `x` missing. Trace the scope stack before entry, during declaration, and after exit. Check both shadowing and assignment to the nearest binding.

## D4: growing loop stack

A long loop eventually consumes large memory even though each statement seems correct. Annotate the stack effect of the condition, conditional jump, body, and back-edge, then inspect which instruction fails to consume a value.
