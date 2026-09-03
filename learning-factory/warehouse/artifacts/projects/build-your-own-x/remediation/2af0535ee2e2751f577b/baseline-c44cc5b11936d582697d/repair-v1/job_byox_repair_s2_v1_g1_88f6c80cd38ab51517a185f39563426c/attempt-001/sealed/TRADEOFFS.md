# Reference tradeoffs

## Direct bytecode emission vs. an AST

Direct emission makes ownership and cleanup unusually simple in C and keeps the exercise focused. It gives up tree inspection, source-to-source transformations, and most optimizations. Adding control flow would make backpatching necessary and may justify an AST or intermediate representation.

## Fixed storage vs. dynamic storage

Fixed arrays provide deterministic, testable failure points and no allocator cleanup paths. The 64-variable, 1024-instruction, and 256-stack limits are intentionally small. Real tools normally grow these structures with checked allocation and explicit ownership.

## Compile-time names vs. runtime environments

Replacing identifiers with slots makes VM execution fast and deterministic. It also bakes the single global scope into compilation. Closures, modules, dynamic lookup, and reflection would require a richer environment model.

## A stack VM vs. native code

Stack bytecode is portable and makes evaluation order visible. It does not teach machine instruction selection, register allocation, object formats, or linking. Those are sensible later projects, not hidden requirements here.

## Immediate output vs. transactional output

The reference streams each `PRINT`; earlier output remains observable if a later instruction fails. Buffering until success would give all-or-nothing output but consume unbounded memory unless another limit were introduced.

## Stable diagnostics vs. recovery

Compilation stops at the first error, making state transitions easy to reason about. A production compiler often synchronizes at semicolons and returns multiple diagnostics, which requires error nodes or carefully specified partial state.
