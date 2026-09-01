# Pebble language requirements

This document is normative. Examples in tests and READMEs do not narrow the contract.

## 1. Source language

Source text is a JavaScript string. Keywords and identifiers are case-sensitive. Identifiers match
`[A-Za-z_][A-Za-z0-9_]*`. A number is one or more ASCII digits, optionally followed by `.` and one
or more ASCII digits. Leading signs belong to unary expressions, not number tokens. Source number
literals must convert to finite JavaScript numbers.

Spaces, horizontal tabs, carriage returns, and newlines separate tokens. A comment starts with `//`
and ends immediately before a line-feed (`\n`) or at end of input. Comments are discarded; `/` by
itself is the division token. A CRLF pair is one newline for locations; a lone carriage return is
whitespace and advances the column. No strings, implicit semicolons, declarations without
initializers, or other punctuation are part of Pebble.

```ebnf
program      = statement* EOF ;
statement    = "let" IDENTIFIER "=" expression ";"
             | "set" IDENTIFIER "=" expression ";"
             | "emit" expression ";"
             | "if" expression block ("else" block)?
             | "while" expression block ;
block        = "{" statement* "}" ;

expression   = equality ;
equality     = comparison (("==" | "!=") comparison)* ;
comparison   = term (("<" | "<=" | ">" | ">=") term)* ;
term         = factor (("+" | "-") factor)* ;
factor       = unary (("*" | "/") unary)* ;
unary        = ("!" | "-") unary | primary ;
primary      = NUMBER | "true" | "false" | IDENTIFIER
             | "(" expression ")" ;
```

Parentheses around an `if` or `while` condition are ordinary expression grouping and are optional.
An `else` always belongs to the immediately preceding `if`. Empty programs and empty blocks are
valid.

## 2. Tokens and locations

`tokenize(source)` returns an array ending in exactly one `EOF` token. Every token has:

```js
{ type, lexeme, literal, line, column }
```

`line` and `column` are one-based locations of the token's first source character. The EOF location
is the position immediately after the final source character. Line feeds advance `line` and reset
`column` to 1; the carriage return in a CRLF pair does not introduce another line.

`type` is one of the uppercase values exported as `TokenType`: `LEFT_PAREN`, `RIGHT_PAREN`,
`LEFT_BRACE`, `RIGHT_BRACE`, `SEMICOLON`, `PLUS`, `MINUS`, `STAR`, `SLASH`, `BANG`, `BANG_EQUAL`,
`EQUAL`, `EQUAL_EQUAL`, `LESS`, `LESS_EQUAL`, `GREATER`, `GREATER_EQUAL`, `IDENTIFIER`, `NUMBER`,
`LET`, `SET`, `EMIT`, `IF`, `ELSE`, `WHILE`, `TRUE`, `FALSE`, or `EOF`.

`lexeme` is the exact source slice, including the original digits for a number. `literal` is the
numeric value for `NUMBER`, the boolean value for `TRUE` or `FALSE`, and `null` otherwise. The EOF
lexeme is the empty string.

## 3. Abstract syntax tree

All nodes have a string `type`. The required fields are:

- `Program { body }` and `BlockStatement { body }`, where `body` is an array of statements.
- `LetStatement { name, initializer }` and `SetStatement { name, value }`, where `name` is a string.
- `EmitStatement { expression }`.
- `IfStatement { condition, consequent, alternate }`, where `consequent` is a block and `alternate`
  is a block or `null`.
- `WhileStatement { condition, body }`, where `body` is a block.
- `NumberLiteral { value }`, `BooleanLiteral { value }`, and `Identifier { name }`.
- `UnaryExpression { operator, argument }` and `BinaryExpression { operator, left, right }`.

Operators are their source spellings. Extra location fields are allowed, but tests compare the
required fields. `parse` must accept either source text or the complete token array returned by
`tokenize`, including its final EOF token.

## 4. Runtime semantics

Pebble has one program-wide variable environment. Braces control statement grouping but do not
introduce lexical scope.

- Statements and operands evaluate from left to right.
- `let` evaluates its initializer and defines a new name. Defining an existing name is an error.
- `set` evaluates its value and replaces an existing binding. Updating an undefined name is an
  error.
- Reading an undefined identifier is an error.
- `emit` evaluates its expression and appends that value to the program's output array.
- An `if` evaluates only its selected branch. A `while` reevaluates its condition before every
  iteration.
- Conditions and unary `!` require booleans. Pebble has no JavaScript-style truthiness.
- Unary `-`, ordering comparisons, and arithmetic require numbers.
- `+` is numeric addition only. There are no implicit conversions.
- Division by positive or negative zero is an error.
- Every Pebble number is finite. If unary or binary arithmetic would produce `NaN`, positive
  infinity, or negative infinity, it fails immediately with `NON_FINITE_NUMBER`; a non-finite value
  is never stored, emitted, or compared.
- `==` and `!=` are strict comparisons: booleans compare with booleans and numbers with numbers;
  values of different types are unequal.

Successful evaluation returns only the array of emitted values. Syntax and runtime failures must be
instances of the exported `PebbleSyntaxError` and `PebbleRuntimeError` classes respectively. Syntax
errors expose one-based `line` and `column` properties for the offending character or token. Step
exhaustion uses the exported `PebbleStepLimitError`, which extends `PebbleRuntimeError`. Messages are
stable and human-readable, but tests do not require one exact wording unless the starter documents
it. Runtime failures expose a stable `code`: `DUPLICATE_VARIABLE`, `UNDEFINED_VARIABLE`,
`TYPE_ERROR`, `DIVISION_BY_ZERO`, `NON_FINITE_NUMBER`, `STEP_LIMIT_EXCEEDED`, `INVALID_OPTIONS`, or
`INVALID_BYTECODE`, as appropriate.

Both execution engines must enforce a positive safe-integer `maxSteps` work budget. The default is
10,000. The tree backend charges one unit when it dispatches a statement and one unit when it
evaluates an expression node, including every evaluation of a loop condition. The VM charges one
unit for every dispatched instruction, including `HALT`. Parsing and compilation are outside these
budgets. These are intentionally backend-specific implementation-work limits, not language-level
fuel: a terminating program may exhaust one backend at a boundary where the other completes. A
nonterminating program must deterministically raise `PebbleStepLimitError` rather than hang.

## 5. Compiler and virtual machine

`compile(program)` accepts a `Program` AST and returns exactly the versioned envelope
`{ format: "pebble-bytecode", version: 1, constants, instructions }`. Constants are finite numbers
or booleans. Instructions are plain objects with an uppercase `op` string and, when the operation
needs one, an `arg`. The supported conceptual operations are constant load, variable
load/definition/update, emit, unary/binary operators, unconditional jump, conditional jump, and
halt. The precise operation names are documented by the starter interface.

Constant operands are valid pool indexes, name operands match the source identifier grammar, and
branch operands are absolute instruction indexes. A conditional jump consumes its boolean condition
whether or not the jump is taken.
The bytecode must not depend on closures, executable JavaScript strings, ambient globals, or source
files. Recompiling the same AST must produce deeply equal bytecode.

`execute(bytecode, options)` validates and runs bytecode without mutating the input object. It must
reject unknown opcodes, invalid operands, invalid jump targets, stack underflow, missing `HALT`, and
instructions after `HALT` that would make the artifact ambiguous. Validation failures are
`PebbleRuntimeError`s.

## 6. Public module API

`starter/src/index.js` must export:

```js
TokenType
OpCode
PebbleSyntaxError
PebbleRuntimeError
PebbleStepLimitError
tokenize(source)
parse(sourceOrTokens)
evaluate(program, options?)
compile(program)
execute(bytecode, options?)
run(source, options?)
```

`run` defaults to the bytecode backend. `{ backend: "tree" }` selects the evaluator and
`{ backend: "vm" }` selects compilation plus VM execution. Unknown backends and invalid option
values are runtime errors. Unknown option keys are also rejected: `run` accepts only `backend` and
`maxSteps`, while `evaluate` and `execute` accept only `maxSteps`. Neither backend may use `eval`,
`Function`, Node's `vm` module, dynamic imports derived from input, or subprocesses.

## 7. Completion criteria

A solution is complete when its public API follows this document, all visible tests pass, additional
tests cover each grammar production and failure class, and both backends agree on terminating
programs whenever neither backend exhausts its own documented work budget. Exact budget-boundary
behavior is compared with the backend-specific rules above rather than treated as general semantic
parity. Malformed input must terminate within bounded resources. Independent validation—not this
document or an agent's claim—determines completion.
