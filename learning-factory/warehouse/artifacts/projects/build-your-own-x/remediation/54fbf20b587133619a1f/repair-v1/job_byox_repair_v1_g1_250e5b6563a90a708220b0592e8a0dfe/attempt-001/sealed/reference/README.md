# Pebble sealed reference

This directory contains the zero-dependency ECMAScript-module reference implementation for the
Pebble language. `index.js` is the public entry point. The implementation is deliberately small,
deterministic, and independent of the learner implementation.

## Language

Pebble source is ASCII-oriented. Identifiers match `[A-Za-z_][A-Za-z0-9_]*`. Number literals match
`DIGIT+ ('.' DIGIT+)?` and must convert to a finite JavaScript number. `//` starts a comment that
ends immediately before the next newline or at end of input.

```text
program     -> statement* EOF
statement   -> "let" IDENTIFIER "=" expression ";"
             | "set" IDENTIFIER "=" expression ";"
             | "emit" expression ";"
             | "if" expression block ("else" block)?
             | "while" expression block
block       -> "{" statement* "}"
expression  -> equality
equality    -> comparison (("==" | "!=") comparison)*
comparison  -> term (("<" | "<=" | ">" | ">=") term)*
term        -> factor (("+" | "-") factor)*
factor      -> unary (("*" | "/") unary)*
unary       -> ("-" | "!") unary | primary
primary     -> NUMBER | "true" | "false" | IDENTIFIER | "(" expression ")"
```

Variables have program-wide scope. Executing `let` for an existing name is a runtime error;
loading or `set`-storing an absent name is a runtime error. Initializers and assigned values are
evaluated before those name checks. Arithmetic, ordered comparison, and unary `-` require numbers.
Unary `!`, `if`, and `while` require booleans. Division by positive or negative zero is an error.
All runtime numbers remain finite; arithmetic overflow raises `NON_FINITE_NUMBER` before its result
can be stored, emitted, or compared. Equality uses JavaScript strict primitive equality over the
validated Pebble value domain, so unlike-typed values compare unequal.
When an `if` condition is false and its optional `else` is absent, execution simply continues.

## Public API

All exports come from `index.js`:

- `tokenize(source)` returns public tokens.
- `parse(sourceOrTokens)` returns a `Program` AST. A supplied token array must end in `EOF`.
- `evaluate(sourceOrAst, options?)` interprets a program.
- `compile(sourceOrAst)` returns bytecode.
- `execute(bytecode, options?)` validates and executes bytecode.
- `run(sourceOrAst, { backend = "vm", maxSteps = 10000 } = {})` parses once and dispatches to the
  VM (`compile` then `execute`) or to `evaluate` when `backend` is `"tree"`. Unknown backends,
  unknown option keys, and invalid option values are `PebbleRuntimeError`s with code
  `INVALID_OPTIONS`.
- `TokenType`, `OpCode`, `BYTECODE_FORMAT`, `BYTECODE_VERSION`, and `DEFAULT_MAX_STEPS` expose frozen
  token/opcode maps and format constants.
- `PebbleError`, `PebbleSyntaxError`, `LexerError`, `ParseError`, `PebbleRuntimeError` (also
  exported as `RuntimeError`), `CompileError`, `BytecodeError`, and `PebbleStepLimitError` (also
  exported as `StepLimitError`) are the error classes. Lexer/parser errors extend
  `PebbleSyntaxError`; bytecode and step-limit errors extend `PebbleRuntimeError`; all language
  errors ultimately extend `PebbleError`.

Runtime failures also carry stable `code` values: `DUPLICATE_VARIABLE`, `UNDEFINED_VARIABLE`,
`TYPE_ERROR`, `DIVISION_BY_ZERO`, `NON_FINITE_NUMBER`, `STEP_LIMIT_EXCEEDED`, `INVALID_BYTECODE`, or
`INVALID_OPTIONS`.
Lexer/parser codes
are `UNEXPECTED_CHARACTER` (or `INVALID_NUMBER`) and `UNEXPECTED_TOKEN`, respectively.

Successful evaluation and execution return only the emitted values, in order:

```js
[/* numbers or booleans */]
```

`evaluate` and `execute` accept `{ maxSteps }`, and `run` also accepts `backend`; the default is
`10000` everywhere. Each fetched VM instruction, including `HALT`, consumes one step. `maxSteps`
must be a positive safe integer. The tree interpreter counts visited statement and expression
nodes rather than VM instructions. These units are intentionally backend-specific: general parity
applies only when neither backend exhausts its budget, and exact cutoff tests follow each backend's
documented accounting.

## Token format

Every token has exactly the public fields shown here; lines and columns are one-based:

```js
{ type: "NUMBER", lexeme: "12.5", literal: 12.5, line: 3, column: 8 }
```

`literal` is the numeric value for `NUMBER`, the boolean value for `TRUE` and `FALSE`, and `null`
for every other token. The final token is
`{ type: "EOF", lexeme: "", literal: null, line, column }` at the position just after the source.

The exact `type` strings are:

```text
LEFT_PAREN RIGHT_PAREN LEFT_BRACE RIGHT_BRACE SEMICOLON
PLUS MINUS STAR SLASH
BANG BANG_EQUAL EQUAL EQUAL_EQUAL
GREATER GREATER_EQUAL LESS LESS_EQUAL
IDENTIFIER NUMBER LET SET EMIT IF ELSE WHILE TRUE FALSE EOF
```

## AST format

AST nodes have only the fields illustrated below. Blocks are nodes, not bare arrays.

```text
Program          { type: "Program", body: Statement[] }
BlockStatement   { type: "BlockStatement", body: Statement[] }

LetStatement     { type: "LetStatement", name: string, initializer: Expression }
SetStatement     { type: "SetStatement", name: string, value: Expression }
EmitStatement    { type: "EmitStatement", expression: Expression }
IfStatement      { type: "IfStatement", condition: Expression,
                   consequent: BlockStatement, alternate: BlockStatement | null }
WhileStatement   { type: "WhileStatement", condition: Expression, body: BlockStatement }

NumberLiteral    { type: "NumberLiteral", value: number }
BooleanLiteral   { type: "BooleanLiteral", value: boolean }
Identifier       { type: "Identifier", name: string }
UnaryExpression  { type: "UnaryExpression", operator: "-" | "!", argument: Expression }
BinaryExpression { type: "BinaryExpression", operator: "+" | "-" | "*" | "/" |
                   "==" | "!=" | "<" | "<=" | ">" | ">=",
                   left: Expression, right: Expression }
```

Grouping affects the tree but does not create its own node.

## Bytecode format

Compilation returns this exact top-level structure:

```js
{
  format: "pebble-bytecode",
  version: 1,
  constants: [/* finite numbers and booleans, in source occurrence order; no deduplication */],
  instructions: [/* instruction objects */]
}
```

The machine is a stack machine. Every operand uses the single field `arg`: `CONSTANT` uses a pool
index, name-taking instructions use an identifier string, and jumps use an absolute zero-based
instruction index.

```text
{ op: "CONSTANT", arg: integer }
{ op: "LOAD", arg: string }
{ op: "DEFINE", arg: string }
{ op: "STORE", arg: string }
{ op: "JUMP", arg: integer }
{ op: "JUMP_IF_FALSE", arg: integer }

{ op: "EMIT" }
{ op: "NEGATE" }  { op: "NOT" }
{ op: "ADD" }     { op: "SUBTRACT" } { op: "MULTIPLY" } { op: "DIVIDE" }
{ op: "EQUAL" }   { op: "NOT_EQUAL" }
{ op: "LESS" }    { op: "LESS_EQUAL" } { op: "GREATER" } { op: "GREATER_EQUAL" }
{ op: "HALT" }
```

Binary instructions pop the right operand and then the left operand, and push one result.
`DEFINE`, `STORE`, and `EMIT` pop one value. `JUMP_IF_FALSE` pops and type-checks its boolean.
Every bytecode object has one `HALT`, exactly at the final array position. Validation rejects an
unknown opcode, unknown/extra operand, bad pool entry or index, invalid name or target, absent or
non-final `HALT`, stack underflow, and a non-empty stack at `HALT`.
