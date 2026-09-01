# Concepts

## A pipeline of representations

A language implementation is easier to reason about when each phase has one job. The lexer turns a
character stream into tokens and owns source positions. The parser turns tokens into a tree whose
shape encodes precedence. An evaluator assigns behavior to that tree. A compiler translates the
same tree into a linear instruction stream, and a virtual machine assigns behavior to those
instructions.

Phase boundaries are useful contracts. Malformed characters should not leak into parser behavior;
an invalid AST should not become a mysterious VM crash. Typed, location-bearing errors make those
boundaries observable.

## Precedence and associativity

Recursive-descent parsing can mirror the grammar: each precedence level consumes the next tighter
level. Repetition produces left-associative operators such as subtraction. Recursion on the right
produces right-associative assignment. Parentheses restart expression parsing at the broadest level.

## Environments and identity

Lexical scope is a chain of maps. Definition touches only the newest map; lookup and assignment walk
outward. This distinction explains both shadowing and mutation of an outer variable. A block needs a
new child environment even when it executes repeatedly.

## Control flow on a stack machine

Expressions naturally leave one value on a stack. Binary instructions consume two and produce one.
Statements also yield values in Sprout, which creates an invariant the compiler can preserve across
branches. Conditional and loop jumps must leave every join point with the same stack and scope
depth. Short-circuit operators are control flow, not eager binary arithmetic.

## Resource limits are semantics

An interpreter runs attacker-controlled structure. Source length, token count, parse recursion,
evaluation steps, instruction dispatch, stack depth, and scope depth are resources. Deterministic
counters make failure reproducible and prevent a valid but non-terminating program from owning the
host process.

## Differential testing

Two engines for one language are a testing advantage. Run the same generated or hand-written
terminating program through each and compare the returned value, output, and normalized error.
Agreement does not prove correctness—both can share a misconception—but disagreement exposes a
real defect quickly.
