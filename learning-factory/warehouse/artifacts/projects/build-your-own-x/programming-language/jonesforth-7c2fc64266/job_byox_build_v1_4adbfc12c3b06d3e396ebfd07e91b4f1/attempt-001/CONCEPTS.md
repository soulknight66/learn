# Concepts

## Concatenative evaluation

A concatenative program places operands before operators. There is no expression tree at runtime:
each word transforms one shared data stack. Stack-effect notation such as ( a b -- a+b ) is a compact
way to state preconditions and results. It also exposes underflow risks before code is written.

## Tokenization without allocation

A bounded input region can be scanned with a cursor and an end pointer. A token is represented by its
start and length rather than copied or NUL-terminated. This is particularly useful in assembly,
where every allocation and lifetime would otherwise need an explicit policy.

## Checked numeric parsing

Decimal parsing is a repeated multiply-by-ten and digit update. Waiting until the final value to ask
whether overflow occurred is too late: intermediate machine operations may already have wrapped.
The most-negative signed integer also has no positive signed counterpart, which makes a
sign-sensitive accumulation strategy worth considering.

## Compiler boundary

This project separates recognition from execution. The compiler maps each valid token to a bounded
instruction representation; the VM later consumes those instructions. Besides making the two phases
observable, this gives the language an atomic compile-error rule: an unknown final token prevents an
earlier output word from running.

## Interpreter state

A small VM needs an instruction pointer, a data-stack base and depth, a code boundary, and temporary
registers. Writing down which state survives helper calls prevents accidental corruption by Linux
syscalls, division instructions, or formatting routines.

## Language design as failure design

The happy path is only part of a language. Literal grammar, truth values, division rounding,
separator bytes, stack limits, and the timing of errors are all semantic choices. Deterministic
failure codes turn those choices into a testable interface rather than unspecified behavior.

## Direct system calls

A no-libc executable owns startup, I/O loops, process termination, and integer formatting. Linux may
return a short read or write even when more work remains. Robust system-call code treats byte counts
as state, not as a promise that one call completes an operation.

