# Code-review exercises

## Signed division helper

Review a proposed helper that checks only a zero divisor before executing `cqo; idiv divisor`.
Identify every input that can trap, specify quotient and remainder signs, and decide where stack depth
may safely be decremented.

## Decimal parser result

Review a parser that returns a single boolean. Its caller treats false as “look up a word.” Explain
why this is insufficient for an all-digit token larger than int64, and design a result convention
that preserves the distinction without allocating memory.

Evaluator answers are kept per exercise under `sealed/review_exercises/`.
