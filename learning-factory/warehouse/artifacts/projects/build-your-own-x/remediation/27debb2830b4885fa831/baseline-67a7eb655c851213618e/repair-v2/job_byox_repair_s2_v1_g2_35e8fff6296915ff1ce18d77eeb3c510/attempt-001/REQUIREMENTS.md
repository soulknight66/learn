# Mica language and implementation requirements

## 1. Public modules

The starter must retain these ES-module exports:

- `tokenize(source)` from `starter/src/lexer.mjs` returns tokens ending in `EOF`.
- `parse(tokens)` from `starter/src/parser.mjs` returns a `Program` AST.
- `interpret(program)` from `starter/src/interpreter.mjs` returns `{ value, output }`.
- `compile(program)` from `starter/src/compiler.mjs` returns `{ constants, code }`.
- `run(chunk)` from `starter/src/vm.mjs` returns `{ value, output }`.
- `execute(source, { backend })` from `starter/src/pipeline.mjs` runs `tree` or `vm` (default:
  `tree`) and returns `{ value, output }`.

`output` is an array of formatted strings. APIs must not write to the console; only the CLI may do
so. Inputs must not be mutated.

## 2. Lexical grammar

Mica source is Unicode text, while identifiers use the intentionally narrow pattern
`[A-Za-z_][A-Za-z0-9_]*`. Spaces, tabs, carriage returns, and newlines separate tokens. A `//`
comment continues to the next newline or end of input.

Token kinds are:

- punctuation: `LEFT_PAREN`, `RIGHT_PAREN`, `LEFT_BRACE`, `RIGHT_BRACE`, `SEMICOLON`;
- operators: `PLUS`, `MINUS`, `STAR`, `SLASH`, `BANG`, `BANG_EQUAL`, `EQUAL`, `EQUAL_EQUAL`,
  `LESS`, `LESS_EQUAL`, `GREATER`, `GREATER_EQUAL`;
- values: `IDENTIFIER`, `NUMBER`, `STRING`;
- keywords: `LET`, `PRINT`, `IF`, `ELSE`, `TRUE`, `FALSE`, `NIL`;
- sentinel: `EOF`.

Numbers use `DIGIT+ ('.' DIGIT+)?` and become finite JavaScript numbers. Strings are delimited by
double quotes and allow only `\n`, `\r`, `\t`, `\"`, and `\\` escapes. Their token literal is the
decoded value. An invalid character, escape, number, or unterminated string raises
`MicaSyntaxError` with a stable code.

Every token carries `{ type, lexeme, literal, span }`. A span has `{ start, end }`; each position has
zero-based `offset` and one-based `line` and `column`. Offsets and columns count JavaScript UTF-16
code units, not Unicode code points or grapheme clusters. Each surrogate code unit therefore adds
one to both the offset and, when on the same line, the column. Only LF (`U+000A`) advances the line
and resets the column to 1. CR (`U+000D`), including the CR in a CRLF pair, advances offset and
column like other non-LF code units; the following LF then advances the line. The end is exclusive.
`EOF` has an empty span at the end of the source.

## 3. Syntactic grammar

```text
program       → declaration* EOF ;
declaration   → "let" IDENTIFIER "=" expression ";" | statement ;
statement     → "print" expression ";"
              | "if" "(" expression ")" block ("else" block)?
              | block
              | expression ";" ;
block         → "{" declaration* "}" ;
expression    → assignment ;
assignment    → IDENTIFIER "=" assignment | equality ;
equality      → comparison (("==" | "!=") comparison)* ;
comparison    → term ((">" | ">=" | "<" | "<=") term)* ;
term          → factor (("+" | "-") factor)* ;
factor        → unary (("*" | "/") unary)* ;
unary         → ("!" | "-") unary | primary ;
primary       → NUMBER | STRING | "true" | "false" | "nil"
              | IDENTIFIER | "(" expression ")" ;
```

Assignment is right-associative. All other binary levels are left-associative. Only an identifier
may appear on the left of `=`. Semicolons are mandatory where shown, including immediately before a
closing brace.

AST nodes are plain objects with a `type` string and a full `span`. Required node types are
`Program`, `LetStatement`, `PrintStatement`, `IfStatement`, `BlockStatement`,
`ExpressionStatement`, `AssignmentExpression`, `BinaryExpression`, `UnaryExpression`, `Literal`,
and `Identifier`. Operator nodes store their source lexeme as `operator`. Literal nodes store
`value` and `raw`; identifiers store `name`.

## 4. Runtime semantics

Mica values are finite numbers, strings, booleans, and `nil` (represented as JavaScript `null`).
Only `false` and `nil` are falsey. Display formatting is: `nil`, `true`, `false`, strings unchanged,
and numbers in JavaScript's ordinary finite decimal representation.

Bindings are mutable and block-scoped. A block gets a fresh scope. A `let` initializer runs before
the name is introduced. Redeclaring a name in the same scope is an error; shadowing an outer name
is allowed. Reads and assignments search from the innermost scope outward. An unknown name is an
error.

Operators follow these rules:

- `+` accepts two numbers (addition) or two strings (concatenation), never mixed values.
- `-`, `*`, `/`, unary `-`, and ordered comparisons accept numbers only.
- division by zero is an error.
- `==` and `!=` use type-sensitive value equality; `nil` equals only `nil`.
- `!` applies Mica truthiness and works on every value.

An `if` evaluates exactly one branch. A block's value is its final statement's value, or `nil` when
empty. `let` and `print` statements have value `nil`; an expression statement has its expression's
value. A program's result is its final statement's value, or `nil` when empty. `print` appends once
to `output` and does not call host console APIs.

## 5. Bytecode contract

Compilation returns an immutable-by-convention chunk with a `constants` array and a `code` array.
Each instruction is `{ op, arg, span }`; instructions without an operand use `arg: null`. Supported
opcodes are:

`CONSTANT`, `LOAD`, `DEFINE`, `STORE`, `NEGATE`, `NOT`, `ADD`, `SUBTRACT`, `MULTIPLY`, `DIVIDE`,
`EQUAL`, `NOT_EQUAL`, `LESS`, `LESS_EQUAL`, `GREATER`, `GREATER_EQUAL`, `PRINT`, `POP`,
`ENTER_SCOPE`, `EXIT_SCOPE`, `JUMP_IF_FALSE`, `JUMP`, and `HALT`.

Constant and jump operands are zero-based integer indexes. Name operands are strings. Jumps target
an instruction within `code`; they may target `HALT`. `STORE` leaves its value on the stack so an
assignment remains an expression. `JUMP_IF_FALSE` consumes its condition. `EXIT_SCOPE` removes only
the lexical environment, not the result value already on the operand stack. A valid compiled chunk
reaches `HALT` with exactly one result value and balanced scopes.

An opcode is always a string. An instruction span is either `null` or `{ start, end }`, with each
position containing own integer `offset`, `line`, and `column` data fields. Offsets are nonnegative;
lines and columns are positive; and an end may not precede its start by offset or by line/column
order.

The `run(chunk)` boundary accepts ordinary inert data graphs: required chunk, instruction, span, and
position fields must be own data properties, and the two arrays must be dense. Accessor-backed or
inherited required fields are malformed. Nonconforming values such as object- or symbol-valued
opcodes must be rejected without coercion. JavaScript `Proxy` objects are outside this API contract
because inspecting them can necessarily invoke user traps; callers crossing a security boundary
must decode and validate an inert serialization before calling `run`.

The VM must raise `MicaRuntimeError` with `E_INVALID_BYTECODE` for malformed in-contract chunks,
rather than executing arbitrary accessors, leaking host exceptions, or silently underflowing the
stack.

## 6. Diagnostics and parity

Syntax failures use `MicaSyntaxError`; execution failures use `MicaRuntimeError`. Each exposes
`name`, stable string `code`, and a `span` or `null`. Required codes include
`E_UNEXPECTED_CHARACTER`, `E_UNTERMINATED_STRING`, `E_INVALID_ESCAPE`, `E_EXPECTED_TOKEN`,
`E_INVALID_ASSIGNMENT`, `E_UNDEFINED_NAME`, `E_DUPLICATE_BINDING`, `E_TYPE`, and `E_DIV_ZERO`.
Malformed chunks use `E_INVALID_BYTECODE`.

For every valid source program, tree and VM execution must return deeply equal `{ value, output }`.
For runtime-invalid programs, both backends must raise `MicaRuntimeError` with the same `code` and
equivalent source span. Exact English messages are not part of the contract.

## 7. Constraints

Use JavaScript ES modules and Node built-ins only. Do not use `eval`, `Function`, third-party parser
generators, network access, subprocesses, global mutable language state, or source-string
special-cases. The implementation must terminate on finite input and must not recurse indefinitely
after a syntax error.
