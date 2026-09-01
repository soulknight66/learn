# Study task: deterministic AST outline

## Goal

Build a small Rust crate that walks a miniature C-shaped AST and produces a deterministic structural outline. The exercise is manager-authored and API-neutral: it is not copied from an official CS420 assignment and must not be described as KECC-compatible.

Time box: six hours.

## Required AST surface

Define an owned Rust data model that can represent all of the following:

- a translation unit containing functions in source order;
- a function with a name, ordered parameters, and a body;
- a block containing statements in source order;
- declaration, expression, return, if/else, and while statements;
- identifier, integer literal, unary, binary, and call expressions.

Parsing and type checking are out of scope. Tests and the demonstration program should construct trees directly.

## Behavioral contract

Provide a public traversal operation and an outline-rendering operation with these properties:

1. Walking is depth-first pre-order. Every represented AST node is visited exactly once, and ordered children are visited in source order.
2. The outline contains one line per visited node. Nesting is visible through a documented indentation rule.
3. Lines identify node kinds and may include stable scalar fields such as names, operators, and literal values. Output must not depend on memory addresses, randomized map order, compiler debug formatting, or platform-specific line endings.
4. Optional branches are handled deliberately. An absent else branch must not cause a panic or a fabricated AST visit.
5. Traversal mechanics and outline formatting are separated enough that a second consumer, such as a node counter, can reuse the traversal without duplicating the recursive walk.
6. Routine output failures are returned to the caller. Do not use global mutable state or panic as ordinary control flow.

You may choose the public types and abstraction style. Document the invariants the API promises and the assumptions it leaves to callers.

## Engineering work

Create a normal Cargo package using the Rust standard library unless you can justify an additional dependency in DESIGN.md. Include:

- a library containing the model, traversal, and renderer;
- a small demonstration binary that constructs at least one nested tree and writes its outline;
- automated tests for an empty translation unit, sibling order, nested control flow, every required node kind, and deterministic exact output;
- a reuse test or demonstration showing a non-rendering consumer using the same traversal;
- rustdoc or equivalent API comments for public items where the contract is not obvious.

At least one test fixture must combine a function, a block, a conditional with an else branch, a loop, and a nested expression. Prefer small focused fixtures in the remaining tests.

## Design record

Write DESIGN.md with:

- the traversal and ordering invariants;
- how traversal and rendering responsibilities are divided;
- the ownership and borrowing model;
- how errors cross the public API;
- one alternative design you considered and its tradeoff;
- which facts would need verification before adapting the component to an external borrowed AST such as KECC's;
- known limitations of this bounded exercise.

Do not claim knowledge of an external API you have not inspected.

## Reproducible evidence

Write EVIDENCE.md that records the working directory, relevant tool versions, and each command actually run with its exit status. Attempt these checks if the local toolchain provides them:

- cargo fmt --check
- cargo clippy --all-targets -- -D warnings
- cargo test
- cargo run

Include enough captured output to identify which check ran and whether it passed. If a tool or component is unavailable, record that fact and the observed error; do not convert an unrun check into a pass. Keep generated build products out of the submitted source unless the harness explicitly asks for them.

## Submission contents

Submit the crate source and manifest, tests, DESIGN.md, EVIDENCE.md, and your responses to COMPREHENSION.md. Keep the work limited to this kickoff and label any optional extension clearly.
