# Concepts

## A pipeline is a sequence of contracts

A compiler is easier to reason about when every stage has a narrow input and output contract:

```text
bytes → tokens → AST → analyzed AST + symbols → bytecode → validated execution
```

Each boundary changes what is known. A scanner knows spelling and positions but not grammar. A parser knows tree structure but should not decide whether a name exists. Static analysis connects names to storage. Code generation lowers meaning to instructions. Validation establishes properties required by the VM.

Keeping these boundaries real makes errors local and tests diagnostic. If `Execute` secretly reparses or directly evaluates, bytecode and validation can be wrong while end-to-end examples still appear correct.

## Scanning and source spans

Scanning is a left-to-right classification problem. The subtle state is usually position tracking: byte offsets are convenient for slicing, while line and column are convenient for people. An exclusive end position composes naturally—adjacent spans meet without overlap—and gives EOF an empty span.

Decide whether positions count bytes or Unicode code points. Pebble deliberately counts bytes, so even malformed UTF-8 is deterministic. Comments are lexical because their contents never reach the grammar.

## Recursive descent parsing

Pebble's prefix grammar maps directly to recursive descent. Each expression begins with enough information to distinguish a literal, name, or binary form. A parser cursor should either advance according to one production or return a positioned error. The hard part is not recognizing valid samples; it is stopping safely and consistently on truncated or caller-forged token streams.

AST spans are semantic infrastructure. Later errors and bytecode instructions can point back to source without retaining parser internals.

## Static semantics and symbol tables

A symbol table answers which declarations are visible and associates them with storage locations. Source order matters here. Inserting a declaration only after its initializer creates a clear rule for self-reference. Assigning dense slots during the same deterministic walk removes name lookup from runtime.

Go maps are useful for lookup but have deliberately unspecified iteration order. Determinism comes from assigning slots while traversing the ordered AST, never by iterating the map.

## Stack-machine compilation

A stack machine makes expression lowering compact. To compile a binary expression, compile its left and right operands, then emit the operator. This mirrors evaluation order. A stack-effect table lets you check the compiler and validate untrusted bytecode using a small abstract interpretation: track depth and initialized slots without calculating values.

Compilation correctness has two sides: emitted instructions implement source semantics, and malformed internal inputs are rejected rather than causing a panic or accidental program.

## Interpreters and virtual machines

The VM is an interpreter for bytecode, not for source syntax. Its loop decodes one instruction, checks runtime-only conditions such as division by zero or numeric overflow, updates local state, and advances. Validation handles structural safety first, making the execution loop's assumptions explicit.

Integer overflow in Go must be detected deliberately because signed operations wrap at the machine level. Division has two distinct exceptional cases: a zero divisor and the one quotient that is outside signed 64-bit range.

## Language design is error design

Syntax is only part of a language. Evaluation order, declaration visibility, numeric limits, error precedence, and diagnostic positions all affect observable behavior. Precise error codes make tools and tests stable; human messages can remain explanatory. Rejecting malformed exported values also matters because a Go package boundary is a trust boundary even if normal parsing would never create them.

## Testing strategy

Useful layers are:

- table tests for tokens, ASTs, and diagnostics;
- instruction-shape tests for compilation;
- validator tests with hand-built hostile bytecode;
- end-to-end semantic tests;
- property or fuzz tests asserting “never panic,” determinism, and no input mutation;
- benchmarks that separate scanning, building, validation, and execution.

A test oracle should target the written contract, not a particular private implementation.
