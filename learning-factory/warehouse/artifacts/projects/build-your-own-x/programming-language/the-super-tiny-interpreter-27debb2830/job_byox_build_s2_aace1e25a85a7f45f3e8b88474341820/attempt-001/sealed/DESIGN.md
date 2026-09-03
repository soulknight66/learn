# Reference design answers

1. A lexeme preserves the user's exact bytes-as-characters; a literal is the lexer's validated,
   decoded value. Escape decoding belongs in lexing so neither execution backend reparses strings.
2. A successful parsing function consumes exactly the tokens in its production and leaves the
   cursor at the first token outside it. A failure throws without attempting open-ended recovery in
   this single-error parser.
3. Assignment recurses on its right operand, producing `a = (b = 4)`. Subtraction folds in a loop,
   producing `(a - b) - 4`. These choices match value propagation and conventional arithmetic.
4. This reference widens the returned inner node's span to include parentheses and records
   `grouped: true`. The marker prevents a grouped identifier from becoming an assignment target;
   evaluators otherwise ignore it.
5. Each scope is a `Map`, and lookup checks `has` before `get`. Therefore a missing key differs from
   a present key mapped to JavaScript `null` (Mica `nil`).
6. The initializer runs before definition, so `let x = x;` inside a block reads an outer `x` when
   one exists. At global scope with no previous `x`, it raises `E_UNDEFINED_NAME`.
7. Both backends implement the same semantic tables for truthiness, formatting, operators, and
   diagnostics. Their control machinery remains separate: recursive AST dispatch versus checked
   instruction transitions. The reference shares small pure semantic helpers to reduce accidental
   prose drift, while tests still inspect compiled structure and VM validation independently.
8. `CONSTANT` and `LOAD` are `+1`; `DEFINE`, `PRINT`, and `POP` are `-1`; `STORE` is `0`; unary ops
   are `0`; binary ops are `-1`; scope and unconditional jump ops are `0`; `JUMP_IF_FALSE` is `-1`
   on either path; `HALT` consumes the one final value when returning it.
9. The compiler emits a `nil` constant at the false destination when no alternate exists. Both
   branches therefore leave one statement value.
10. Jump instructions are emitted with `-1`, and patching replaces the whole instruction object.
    No unresolved operand remains when the chunk is returned.
11. The VM checks chunk shape, Mica-compatible constants, opcode membership, constant indexes,
    identifier operands, in-range integer jump targets, and null operands on operand-free opcodes.
    Dynamic checks cover stack depth, names, scope balance, program counter, and an instruction
    limit.
12. Public examples establish a few concrete parses and executions. Adversarial checks are needed
    for scope leakage, dead-branch evaluation, malformed chunks, stack balance, and looping hostile
    jumps; generated trees broaden operator and precedence coverage.
13. Functions would require environment lifetime beyond a block, call frames, arity and return
    instructions, and probably resolved lexical addresses rather than repeated string lookup.
14. Production diagnostics would want source identity, excerpts, multi-span labels, recovery hints,
    causality, localization, and a structured serialization contract.
