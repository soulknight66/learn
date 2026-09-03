# Alternative designs

## Tree-walking interpreter

Build an AST with arena allocation, then evaluate it recursively.  This gives
excellent source correspondence and is easiest to extend with functions, but
deep guest structure consumes the host C stack unless evaluation is made
iterative.

## Register bytecode

Compile expressions into numbered registers and basic blocks.  Fewer dispatches
and explicit data flow help optimization, at the cost of a more complicated
allocator and a less approachable self-interpreter.

## Pratt parser plus AST

A Pratt parser collapses the expression precedence ladder into binding-power
tables.  It handles future postfix and ternary syntax elegantly.  The explicit
recursive-descent ladder in the reference was chosen because each grammar rule
is directly visible to learners.

## Source-level bootstrap

Extend Ember-C with arrays, character input, functions, and indirect data
structures; rewrite its lexer, parser, compiler, and VM in that extended subset;
then compare stage-two and stage-three artifacts.  This is the honest route to
full textual self-hosting, but far beyond this bounded artifact.
