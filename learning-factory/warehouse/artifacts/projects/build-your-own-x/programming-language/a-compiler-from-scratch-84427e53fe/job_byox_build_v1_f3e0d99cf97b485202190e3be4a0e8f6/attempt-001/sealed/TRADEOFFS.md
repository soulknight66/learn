# Implementation tradeoffs

## Hash AST versus node classes

Symbol-keyed hashes keep the required public schema transparent and easy to inspect. They give up constructor-time validation and exhaustive dispatch. The compiler therefore validates important shapes and converts unknown nodes into `CompileError`; dedicated immutable node classes would be safer in a larger compiler.

## Monotonic local slots

Every declaration receives a new slot, even after its lexical scope ends. This simplifies resolution, makes output deterministic, and avoids accidental stale-value reuse. It can over-allocate for large mutually exclusive branches. Slot lifetime analysis is deliberately outside this challenge.

## Direct instruction arrays

Arrays make emitted bytecode visible to learners and easy to compare. They are mutable and do not carry source spans. A production representation would likely use immutable encoded instructions plus a side table for diagnostics.

## Runtime validation

The VM validates the shape and operands of all instructions before starting, then checks stack and value rules on the executed path. It does not perform a full control-flow stack analysis, so an unreachable stack-underflow instruction can remain undetected. This is adequate for the teaching boundary but listed as a production gap.

## No optimizer

The reference emits straightforward stack code and does not fold constants, remove dead branches, or reuse slots. Stable, literal lowering makes compiler bugs easier to localize and keeps tests about semantics rather than optimization choices.
