# Concepts to master

## A front end is a sequence of contracts

The scanner turns characters into located tokens. The parser turns tokens into a tree whose shape
encodes precedence and associativity. Execution should never need to guess what the source meant.
Keeping these phases separate makes a failure attributable and lets both engines reuse one front end.

## Recursive descent mirrors the grammar

One parser method per precedence level makes binary precedence visible in call structure. Loops build
left-associative operators; recursion on the right builds right-associative assignment. The token on
an AST node is also a compact source map for diagnostics.

## Environments implement lexical scope

An environment is a current binding map plus a parent link. Lookup and assignment walk outward;
definition touches only the current map. Initializing before defining prevents `let x = x;` from
silently reading the new, not-yet-initialized binding.

## Compilation makes control flow concrete

An AST `if` has branches. Bytecode has instruction indexes and jumps. A compiler emits a placeholder,
remembers its index, then patches its target once the destination is known. Short-circuit operators
use the same mechanism, preserving a value on the operand stack along one path and replacing it along
the other.

## A VM has invariants

For every opcode, state the stack shape before and after it. Every jump target and constant index must
be validated. Scope entry/exit must balance. These invariants turn corrupt bytecode into a controlled
language error instead of a Java crash.

A compiler-emitted `TICK` is semantic instrumentation: placing it at the same statement boundaries as
the tree interpreter makes a resource limit part of shared language behavior rather than an accidental
property of instruction selection.

## Differential testing is an oracle amplifier

Two independently structured engines can check one another. Generate or enumerate valid programs,
run both, then compare output and error category. Agreement is not proof—shared front-end and semantic
bugs remain possible—but disagreements sharply localize defects.
