# Concepts, revealed in layers

Read one layer, make your own design, then continue.

## Layer 1: text is already structured

A lexer turns ambiguous-looking characters into an unambiguous token stream. Track the start position
of each token before consuming it. Decide in one place how CR, LF, and CRLF move that position. Test
prefix pairs such as `!`/`!=` and `<`/`<=` at end of input.

<details>
<summary>Questions to unlock before parsing</summary>

- Is a keyword recognized while scanning, or after scanning an identifier?
- Which component owns integer range checking?
- Where does the EOF token point after a trailing CRLF?

</details>

## Layer 2: precedence is tree shape

The VM cannot repair an incorrectly grouped expression. A recursive-descent parser can dedicate one
function to each precedence row, with a loop for left-associative binary operators and recursion for
right-associative unary operators. Statements need deliberate lookahead because both declaration and
assignment contain an identifier and `=` at different positions.

<details>
<summary>Invariant worth writing down</summary>

On successful return, each parse function has consumed exactly its construct and left the first token
belonging to its caller untouched. On failure, the reported token is the earliest point where the
construct became impossible.

</details>

## Layer 3: names are not strings at runtime

Lexical resolution maps each identifier occurrence to a slot while scopes are still known. A stack of
dictionaries models nested scopes. The timing of insertion matters for self-initializers; assignment
searches from the innermost dictionary outward.

<details>
<summary>Lifetime versus identity</summary>

This challenge allows a fresh slot for every declaration, which keeps resolution simple. Reusing slots
after a block can reduce the header count, but only if shadowing and loop re-entry do not confuse name
identity. Optimize this only after correctness tests pass.

</details>

## Layer 4: emission is bookkeeping

Stack code follows expression postorder: emit the left expression, then the right, then the operator.
Forward branch destinations are unknown, so reserve fixed-width operand bytes and patch them once the
destination offset is known. Record offsets relative to the code section—not Python list indices and
not whole-file offsets.

<details>
<summary>Compiler stack invariant</summary>

Every expression leaves one value. Every statement leaves none. Both arms of a conditional therefore
arrive at their merge with the same depth, and a loop body arrives back at its condition with its entry
depth.

</details>

## Layer 5: decoding is not validation

Knowing instruction boundaries is only the first pass. Validation also follows control-flow edges and
propagates abstract stack depth. A destination must be an instruction boundary, and a merge must agree
on depth. Do this before execution so malformed code cannot print something and fail afterward.

<details>
<summary>Why a step limit is separate</summary>

Structural verification proves the machine will not misinterpret bytes or underflow its stack. It
cannot prove a valid loop terminates. Count dispatched instructions and reject a non-positive or
boolean limit at the API boundary.

</details>

## Layer 6: host semantics are not language semantics

Python integers do not overflow, and Python `//` rounds toward negative infinity. Minnow requires
signed-64 checks and truncation toward zero. Implement those rules explicitly and test mixed-sign
division and remainder. Avoid float conversion, which loses precision near 64-bit limits.
