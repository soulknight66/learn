# Concepts map

## Scanner to tokens

The scanner is a bounded cursor over bytes, not a collection of null-terminated substrings. Record the
start offset, length, line, and column for each token. Keyword recognition is an exact-length check.
Accumulate integer literals with a pre-multiply overflow guard.

## Recursive-descent precedence

Each expression function consumes operators at one precedence and delegates operands to the tighter
level below it. This makes associativity visible: the loops for binary arithmetic yield left
associativity, while recursive unary parsing yields right nesting. A parser function should leave one
runtime value on the abstract stack when successful.

## Names and scopes

A compact compiler can keep a linear symbol table. Store name bytes, declaration depth, and a stable VM
slot. Search backward for nearest-scope resolution. Leaving a block removes compile-time visibility,
while slot numbers can remain stable in the generated program.

## Bytecode and backpatching

Forward branch destinations are unknown when their branch instruction is emitted. Emit a placeholder,
compile the controlled block, then patch the operand. Validate both emission and patch offsets. Loops
use a known backward target. Logical short-circuiting is control flow too: it cannot be implemented as
an eager arithmetic instruction without changing observable errors and step usage.

## VM invariants

Give each opcode a stack effect and check it before reading. The compiler tracks the intended effect;
the VM still defends its own boundary. The instruction pointer must be checked before fetch and jump.
Every dispatched instruction consumes one unit from the step budget, including branches and `HALT`.

## C-defined arithmetic

Signed overflow is undefined behavior in C. Check operands before addition, subtraction,
multiplication, division, remainder, and negation. Comparison itself is safe. Bounds and allocation
sizes deserve the same discipline as language arithmetic.

## Determinism and ownership

The same source, options, and input-independent environment must yield the same result, output, and
diagnostic. Separate immutable compiled data from per-run mutable state so repeat execution is reliable
and cleanup has one obvious owner.
