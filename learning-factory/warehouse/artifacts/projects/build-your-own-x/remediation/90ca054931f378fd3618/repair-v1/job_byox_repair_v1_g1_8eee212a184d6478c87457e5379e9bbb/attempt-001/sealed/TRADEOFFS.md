# Tradeoffs

## Direct bytecode versus AST evaluation

Direct bytecode avoids a second large node arena and gives the step budget a crisp meaning. It
also exposes jump patching earlier than an AST interpreter would. The cost is that parsing and
lowering errors are more tightly coupled, and dead instructions after `return` remain in the code
table. An AST-first design is described in `alternatives/README.md`.

## Fixed capacities versus dynamic structures

Fixed post-allocation tables make exhaustion behavior deterministic and easy to review. They can
waste memory: every VM frame reserves all 256 local slots. Dynamically sized frames and vectors
would reduce the footprint but add allocation failure paths and lifetime ownership to the lesson.

## Bounded recursive descent versus an iterative expression parser

Recursive descent mirrors the grammar, but source-controlled grouping and statement nesting also
consume the host stack. The reference makes 512 levels part of the language profile and diagnoses
the next level before descending. Unary prefixes are easy to consume iteratively, so they do not
need this extra restriction. A fully iterative operator/statement parser could admit deeper syntax,
but its explicit state machine would substantially obscure the precedence lesson; changing to that
design would also require a new normative limit and boundary matrix.

## One function scope versus lexical block scope

One namespace means a declaration can never shadow another local. That diverges from C but avoids
scope-stack restoration and ambiguous slots in a compact compiler. Adding lexical scope would be
a good extension only after tests cover declaration lifetime and shadowing.

## Eager compilation versus streaming execution

Compiling the complete file enables forward calls and catches undefined functions before any
output occurs. A streaming interpreter could start sooner and use less code storage, but source
errors might then appear after partial effects.

## Built-in print versus a native FFI

A single `print` statement keeps the effect boundary narrow. A general native-call interface would
make examples richer but would invalidate deterministic isolation unless every call were
carefully capability-scoped and budgeted.

## Staged bootstrap versus full self-hosting

The nested stack interpreter fits the specified subset and demonstrates two interpretation
layers. A full source-level self-host would require at least source bytes, indexed collections,
and substantially more memory semantics. Calling the smaller demonstration “full self-hosting”
would be misleading, so the artifact names its boundary explicitly.
