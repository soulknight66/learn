# Concepts behind the challenge

## Tokens are a compatibility boundary

A lexer replaces raw bytes with classified spans. Keeping line and column on
each token lets later phases report the location that caused the problem rather
than the location at which confusion finally became visible. Longest-match is
important for `<=` versus `<` followed by `=`.

## Precedence emerges from parser structure

In recursive descent, each precedence level parses operands using the next
tighter level. Repetition implements left associativity; recursion implements
the prefix operators. The parser should construct a representation, not execute
as it recognizes text, because both the interpreter and compiler consume the
same validated program.

## Syntax and meaning are separate questions

`x = 3;` has valid syntax even when `x` was never declared. A separate validation
walk keeps name policy out of parsing and prevents the interpreter and compiler
from disagreeing about which programs are legal.

## An interpreter is an executable specification

Tree walking maps each node directly to its meaning. It is easy to inspect and
therefore useful as a comparison oracle for compiled programs. In C, implement
Mica's wraparound with unsigned operations and bit-preserving conversion instead
of invoking undefined signed overflow.

## Control flow becomes labels and branches

The native backend turns structured `if` and `while` nodes into unique labels,
conditional jumps, and backward edges. Expression code can use a stack-machine
discipline: evaluate operands, preserve one, and combine them. Track stack
alignment at calls because the host ABI is part of correctness.

## Diagnostics and limits are language design

Rejecting excessive source, nesting, nodes, variables, or execution steps makes
failure deterministic. These limits are observable behavior, not merely
implementation details. A useful compiler specifies errors as deliberately as
successful output.
