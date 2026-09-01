# Reference design

## Representation policy

The reference uses plain data across every boundary. Tokens carry decoded literals and one-based
locations. AST nodes carry no methods or environment links. Bytecode contains primitive constants
and instruction records. This makes differential assertions direct and keeps serialization possible,
although the VM still validates the in-memory form before use.

A compound node's location is the token that introduces its operation: a statement keyword or opening
brace, an operator for unary/binary/logical nodes, and the identifier for assignment. Parentheses do
not overwrite an inner expression's location.

The frozen keyword table has a null prototype, and lookup also requires an own property. Therefore
every non-keyword admitted by the identifier grammar—including names inherited by ordinary
objects—stays an `IDENTIFIER` token.

## Parser

One method implements each precedence level. Binary loops make arithmetic, comparison, equality, and
logical operators left-associative. Assignment parses its right side recursively and accepts only an
already-parsed `Identifier` on the left. Because grouping does not survive as an AST node, a grouped
identifier remains a valid assignment target. A shared recursion guard covers nested statements,
parenthesized expressions, unary chains, and assignment chains.

## Tree engine

An environment owns one `Map` plus an optional parent. Define checks only the current map; get and
assign walk outward. Executing a `BlockStatement` always constructs a child, including on every loop
iteration. The evaluator increments its budget on entry to each statement or expression node.

Logical expressions are handled before ordinary binary dispatch. The left value determines whether
the right node is visited, and the chosen operand is returned unchanged. Centralized unary, binary,
truthiness, and formatting helpers are shared with the VM to reduce accidental semantic drift.
The evaluator flattens parser-produced left spines for binary and logical expressions, avoiding host
recursion proportional to the number of ordinary left-associative operators while retaining one
language step per AST node.

## Compiler invariant

Every compiled statement leaves exactly one value on the operand stack. Sequential statements emit a
`POP` between results. Blocks enter a lexical scope, compile their sequence (or push `NULL`), then
exit while leaving the operand stack untouched.

An `if` keeps its condition until the chosen edge, pops it on both edges, and makes each branch leave
one result. A loop starts with a `NULL` result. On a true iteration it discards the condition and the
previous result before compiling the body; on exit it discards only the false condition. Thus a loop
uses constant stack space and retains the final body value.

`or` branches around its right expression when the left is truthy. `and` branches around it when the
left is falsey. The skipped edge retains the left operand; the evaluating edge pops it first. Both
edges therefore join at the same stack height.

Compilation uses the same left-spine technique for binary and logical chains. Genuinely nested right
operands still pass through the compile-depth guard, while a flat expression admitted by the parser
does not acquire a compiler-only recursion failure.

## Bytecode validation

Structural checks reject unknown or extra fields, invalid primitive constants, bad locations,
argument mismatches, invalid names, invalid indexes, bad targets, and misplaced halts. A work-list
abstract interpreter then associates each reachable instruction with `(stackDepth, scopeDepth)`.
Each opcode applies a transfer function. Underflow, configured maxima, and mismatched join states are
errors. The final reachable halt requires exactly one value and the global scope.

Validation finishes before dispatch. Runtime maps mirror tree environments, while operand behavior
uses the shared semantic helpers. The VM budget counts dispatched instructions, so its numeric limit
is deterministic but not expected to expire on the same source construct as the tree budget.
The constants and code containers must be ordinary dense arrays whose prototype is exactly the
intrinsic `Array.prototype`; the validator rejects null, subclass, and custom prototypes before
reading elements, and it never invokes an inherited array method on untrusted input.
