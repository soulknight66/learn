# Alternative Pebble designs

These notes are sealed because they disclose implementation choices and useful
solution directions. They are recommendations and comparisons, not additional
implemented variants.

## Expression parsing

The reference shape can be expressed with precedence climbing: parse a unary
seed, then consume binary operators while their precedence is high enough,
raising the right-hand minimum for left-associative operators. A Pratt parser is
a natural extension when Pebble gains calls, indexing, or operators with varied
fixity. A ladder of recursive-descent functions (`equality`, `comparison`,
`term`, `factor`, `unary`) is longer but often easiest for a first-time reader
to debug.

Keep operator metadata in one table if syntax grows. Duplicating precedence in
the parser, pretty-printer, and documentation invites drift.

## Runtime state

A `Map`-backed environment makes arbitrary identifier keys safe and makes
declaration checks explicit. A flat environment matches the small language.
Nested `Environment` frames with a parent pointer are the incremental route to
lexical scope; JavaScript objects and their prototype chain should not be used
as a substitute for language scope.

Persistent maps would make snapshots and time-travel debugging easier but add
allocation and conceptual cost that this educational compiler does not need.

## Intermediate representation

Direct AST interpretation is excellent for tracing language semantics. A
separate small stack instruction set exposes lowering, control-flow patching,
and VM execution without requiring machine code. Absolute jump targets are
easy to inspect; relative targets make relocation and concatenation easier but
require a rigorously shared origin convention.

A register VM may emit fewer instructions and reduce stack-height validation,
but requires register allocation or explicit temporary management. SSA would
teach optimization well, yet it is a disproportionate next step before basic
bytecode validation and source locations are complete.

## Compiler organization

Tagged-node `switch` statements are direct and keep the accepted AST surface
visible. Visitor objects make extension and instrumentation easier but spread
one compilation phase across more methods. Whichever is chosen, reject unknown
tags explicitly and preserve source spans through AST and bytecode metadata so
runtime errors can point back to source.

## Error and resource contracts

Typed Pebble errors with stable codes are preferable to matching message text.
Tree visits and VM dispatches naturally count different kinds of work. If a
single portable `maxSteps` contract is required, define abstract fuel points in
the language and enforce equivalent points in both backends. Otherwise name the
limits separately and promise termination bounds, not identical cutoff points.
