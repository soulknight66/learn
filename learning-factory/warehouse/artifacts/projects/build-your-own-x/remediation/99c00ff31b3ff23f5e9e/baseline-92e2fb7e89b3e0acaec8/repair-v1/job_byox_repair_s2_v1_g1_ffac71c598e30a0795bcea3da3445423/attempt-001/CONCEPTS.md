# Concepts behind Pebble

## Tokens carry evidence

A lexer does more than classify bytes. Retaining each token's starting line and
column lets later phases report where an invalid construct began. Numeric
conversion is part of lexing because overflow is a property of the literal,
not of an eventual arithmetic operation.

## Precedence is parser structure

Recursive descent can encode precedence as one function per grammar level.
Each level parses an operand from the tighter level, then folds a sequence of
its own operators from the left. Unary recursion and parenthesized expressions
need an explicit depth budget when input is untrusted.

## Syntax and names are separate concerns

The parser establishes shape. A later resolver checks declaration order,
duplicate names, and unknown uses. Keeping these jobs separate prevents the
interpreter and compiler from accidentally accepting different programs.

## One AST, two meanings

The interpreter recursively computes an expression value and mutates an
environment. The compiler recursively emits instructions that leave the same
value in `%rax`. Differential tests can run both paths on one source program;
any mismatch is evidence that at least one implementation violates the shared
semantics.

## ABI details are language correctness

On System V AMD64, integer call arguments use registers, `%rax` has a special
role for variadic calls, and the stack must be aligned before a call. Signed
division truncates toward zero, and signed remainder follows the dividend's
sign. The `%rdx:%rax` dividend can trap for either `idivq` operation on the
`INT64_MIN, -1` pair, even when only the remainder is wanted, so both Pebble
operators reject that pair before the instruction. Those machine rules are
observable parts of a correct backend, not mere optimization details.

## Determinism needs budgets

An interpreter for `while 1 {}` will not terminate without a fuel counter.
Input-size, nesting, variable-count, process-time, and step limits make failure
repeatable. The compiler must include an equivalent counter if compiled and
interpreted behavior is meant to match.

Test timeouts need the same whole-tree reasoning. A direct child can fork a
descendant that keeps captured pipes open. Starting each command in a fresh
process group, terminating the group with a bounded escalation, and retaining
only a fixed amount from each stream keeps the harness deterministic.

## Atomic artifacts

Writing assembly directly to the requested path can leave a truncated file
after a compiler error. Generate a sibling temporary, close it successfully,
then rename it. A visible output name should mean a complete generation step,
not simply that `fopen` once succeeded.
