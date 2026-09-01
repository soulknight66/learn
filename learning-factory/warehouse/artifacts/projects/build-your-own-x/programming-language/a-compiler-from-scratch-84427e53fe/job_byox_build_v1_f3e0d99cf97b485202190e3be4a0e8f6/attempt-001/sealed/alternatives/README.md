# Alternative designs

## Tree-walking interpreter

Execute AST nodes directly with chained environment hashes. This shortens the implementation and produces natural source-local errors, but it collapses compilation and execution, moves name mistakes later, and does not teach jump lowering or bytecode validation.

## Named-variable bytecode

Emit `LOAD "x"` and `STORE "x"` with runtime scope dictionaries. Disassembly is readable, but lexical binding and undeclared-name checks become runtime concerns. Shadowing also requires explicit scope-enter/scope-leave instructions.

## Pratt parser

A Pratt parser expresses precedence in a table and scales well as operators grow. Recursive descent was selected because Pebble has few fixed precedence levels and the grammar-to-method correspondence is useful for this challenge.

## Register bytecode

Three-address instructions avoid implicit stack effects and simplify some data-flow analyses. They require temporary allocation and a wider instruction schema. Stack code keeps the initial compiler smaller while still exposing control-flow lowering.

## Direct Ruby generation

Translating Pebble into Ruby source would outsource arithmetic and control flow but creates semantic mismatches (truthiness, integer width, signed modulo) and a serious code-injection boundary. It is intentionally excluded.
