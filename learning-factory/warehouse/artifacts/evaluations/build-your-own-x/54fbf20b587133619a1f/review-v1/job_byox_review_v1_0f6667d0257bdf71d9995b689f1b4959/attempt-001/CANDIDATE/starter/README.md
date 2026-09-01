# Pebble learner starter

Pebble is a deliberately small language for learning how a source string becomes tokens, an AST,
and executable behavior. This directory is an **incomplete** zero-dependency ESM implementation.
Its public interfaces and module boundaries are ready to use, but the language algorithms are left
as explicit `TODO`s.

Run the public checks from this directory with:

```sh
npm test
```

No install step is needed. Node.js 20 or newer is sufficient.

## Language

A Pebble program is a sequence of statements. Semicolons end `let`, `set`, and `emit` statements;
blocks do not need a trailing semicolon.

```pebble
let count = 0;
while count < 3 {
  if count == 1 {
    emit true;
  } else {
    emit count;
  }
  set count = count + 1;
}
```

The grammar is:

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
primary     -> NUMBER | "true" | "false" | IDENTIFIER
             | "(" expression ")"
```

Parentheses around an `if` or `while` condition are ordinary expression grouping and are optional.
`//` starts a comment that continues through the end of the line. Identifiers start with an ASCII
letter or `_` and continue with ASCII letters, digits, or `_`. Numbers use ASCII digits with an
optional decimal part: `[0-9]+(\.[0-9]+)?`. A number must be finite.

Pebble has only number and boolean values. Arithmetic and ordering operators require numbers,
unary `-` requires a number, unary `!` requires a boolean, and conditions require booleans. Equality
compares values without coercion. Division by positive or negative zero is an error.

There is one program-wide variable environment, including inside blocks. Executing `let` for a name
that is already defined is an error. Reading or `set`-ting an undefined name is an error. `emit`
appends a value to the program's returned output array.

## Public API

Everything needed by callers is exported from `src/index.js`:

```js
TokenType
OpCode
PebbleSyntaxError
PebbleRuntimeError
PebbleStepLimitError
tokenize(source)
parse(sourceOrTokens)
evaluate(ast, { maxSteps } = {})
compile(ast)
execute(bytecode, { maxSteps } = {})
run(source, { backend = "vm", maxSteps } = {})
```

`evaluate` is the tree-walking backend. `compile` plus `execute` is the default bytecode backend.
Both execution paths return the values produced by `emit`, in order. `maxSteps` is a positive
integer work budget, defaulting to 10,000, used to stop runaway programs; exhausting it throws
`PebbleStepLimitError`. The precise unit of work may differ between backends, so callers should
treat it as a safety bound, not a portable instruction count.

Options are closed records: `run` accepts only `backend` and `maxSteps`; `evaluate` and `execute`
accept only `maxSteps`. Unknown keys, `null` values, and values of the wrong type use
`INVALID_OPTIONS`.

`compile` returns a bytecode container with this public envelope:

```js
{
  format: "pebble-bytecode",
  version: 1,
  constants: [],
  instructions: []
}
```

Instructions are plain `{ op, arg? }` objects. `op` is one of the strings exported by `OpCode` in
`src/opcodes.js`; `arg` is omitted for operations that do not take one. The bytecode contract is:

| Operation | Argument | Stack/flow effect |
| --- | --- | --- |
| `CONSTANT` | constant-pool index | push that constant |
| `LOAD` | variable name | push the current binding |
| `DEFINE` | variable name | pop and define a new binding |
| `STORE` | variable name | pop and update an existing binding |
| `EMIT` | none | pop and append to outputs |
| `NEGATE`, `NOT` | none | replace the top value with its unary result |
| `ADD`, `SUBTRACT`, `MULTIPLY`, `DIVIDE` | none | pop right then left; push the arithmetic result |
| `EQUAL`, `NOT_EQUAL`, `LESS`, `LESS_EQUAL`, `GREATER`, `GREATER_EQUAL` | none | pop right then left; push the comparison result |
| `JUMP_IF_FALSE` | absolute instruction index | pop a boolean and jump when it is false |
| `JUMP` | absolute instruction index | jump unconditionally |
| `HALT` | none | finish execution |

`HALT` must be the last instruction. Compiling the same AST repeatedly must produce deeply equal
plain data. `execute` must validate bytecode before running it, including indexes, jump targets,
stack use, opcode/argument shapes, and the unique final `HALT`; validation failures are Pebble
runtime errors. The input bytecode object must not be mutated.

## Token contract

`tokenize` returns tokens in source order and one final `EOF` token. Every token has:

```js
{
  type: TokenType.NUMBER,
  lexeme: "12.5",
  literal: 12.5,
  line: 1,
  column: 1
}
```

Lines and columns are one-based and identify the first character of the token. `literal` is the
numeric value for `NUMBER`, the boolean value for `TRUE`/`FALSE`, and `null` otherwise. The exact
`TokenType` strings live in `src/tokens.js`.

## AST contract

Parsers may add source-location metadata, but these fields and spellings are required:

```text
Program          { type, body: Statement[] }
BlockStatement   { type, body: Statement[] }
LetStatement     { type, name: string, initializer: Expression }
SetStatement     { type, name: string, value: Expression }
EmitStatement    { type, expression: Expression }
IfStatement      { type, condition: Expression,
                   consequent: BlockStatement, alternate: BlockStatement | null }
WhileStatement   { type, condition: Expression, body: BlockStatement }
NumberLiteral    { type, value: number }
BooleanLiteral   { type, value: boolean }
Identifier       { type, name: string }
UnaryExpression  { type, operator: "-" | "!", argument: Expression }
BinaryExpression { type, operator: string, left: Expression, right: Expression }
```

## Error contract

Malformed source throws `PebbleSyntaxError`. Language failures during either backend throw
`PebbleRuntimeError` (or the `PebbleStepLimitError` subclass). Runtime error codes used by the public
contract are:

- `DUPLICATE_VARIABLE`
- `UNDEFINED_VARIABLE`
- `TYPE_ERROR`
- `DIVISION_BY_ZERO`
- `STEP_LIMIT_EXCEEDED`
- `INVALID_OPTIONS`
- `INVALID_BYTECODE`

Messages should be useful to a person, but callers should use the class and code rather than exact
message text.

## Suggested implementation order

1. Complete `Lexer.tokenize` and make the token tests pass.
2. Complete `Parser.parse`, starting with literals and precedence before statements and blocks.
3. Complete the tree-walking `Evaluator` with a single environment and a step budget.
4. Implement the documented instruction contract in `Compiler` and `VirtualMachine`.
5. Check that both backends produce the same outputs and error categories.

Search for `TODO` in `src/` to find every learner-owned implementation point.
