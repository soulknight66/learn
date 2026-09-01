# Requirements

## 1. Public API

Use ECMAScript modules and export `tokenize`, `parse`, `interpret`, `compile`, `runBytecode`, and
`execute` from `starter/src/index.js`. Inputs must not be mutated. Do not use dynamic code execution,
host I/O, subprocesses, the network, or environment variables.

`execute(source, options)` selects `options.engine`, defaulting to `tree`. Unknown engines are an
ordinary `TypeError`. Both engines return a fresh `{ value, output }` object. `output` contains
formatted strings; it is never printed by the implementation.

## 2. Lexical grammar

The source alphabet is Unicode, but identifiers are deliberately ASCII:

```text
identifier  := [A-Za-z_][A-Za-z0-9_]*
number      := [0-9]+ ("." [0-9]+)?
string      := '"' character* '"'
character   := any code unit except raw newline, carriage return, '"', or '\\'
             | '\\' ('"' | '\\' | 'n' | 'r' | 't')
comment     := "//" code-units-until-line-end
```

Recognize punctuation `(`, `)`, `{`, `}`, `;`; operators `+ - * / ! != = == < <= > >=`; and the
keywords `let`, `print`, `if`, `else`, `while`, `true`, `false`, `null`, `and`, `or`. Whitespace and
comments produce no token. A trailing `EOF` token is mandatory.

Every token has `{ type, lexeme, literal, line, column }`. Lines and columns are one-based and point
to the token's first code unit. Literal is decoded for strings, numeric for numbers, and `null` for
other tokens. Reject unknown characters, bad escapes, raw line breaks in strings, unterminated
strings, and non-finite numeric values with `LexError`.

Default limit: at most 1,000,000 source code units and 200,000 non-EOF tokens. Options may lower,
but not disable, those limits.

## 3. Syntax and AST

```text
program        -> statement* EOF ;
statement      -> "let" IDENTIFIER "=" expression ";"
                | "print" expression ";"
                | "if" "(" expression ")" block ("else" block)?
                | "while" "(" expression ")" block
                | block
                | expression ";" ;
block          -> "{" statement* "}" ;
expression     -> assignment ;
assignment     -> logic_or ("=" assignment)? ;
logic_or       -> logic_and ("or" logic_and)* ;
logic_and      -> equality ("and" equality)* ;
equality       -> comparison (("==" | "!=") comparison)* ;
comparison     -> term ((">" | ">=" | "<" | "<=") term)* ;
term           -> factor (("+" | "-") factor)* ;
factor         -> unary (("*" | "/") unary)* ;
unary          -> ("!" | "-") unary | primary ;
primary        -> NUMBER | STRING | "true" | "false" | "null"
                | IDENTIFIER | "(" expression ")" ;
```

Reject missing delimiters, invalid assignment targets, and trailing input with `ParseError`. The
left side of `=` is valid only when parsing `logic_or` produces an `Identifier` node. Because
parentheses do not produce an AST node, `(name) = value` and further-parenthesized identifiers are
valid assignment forms. Parsing is fail-fast. Enforce a default recursive parse-depth limit of
1,000; ordinary repetitions in the left-associative precedence productions do not consume that
recursive-depth budget.

Use these node shapes; each node also contains `loc: { line, column }`:

- `Program { body }`
- `LetStatement { name, initializer }`, where `name` is an `Identifier`
- `PrintStatement { expression }`, `ExpressionStatement { expression }`
- `BlockStatement { body }`, `IfStatement { test, consequent, alternate }`
- `WhileStatement { test, body }`
- `AssignmentExpression { name, value }`
- `LogicalExpression { operator, left, right }`, `BinaryExpression { operator, left, right }`
- `UnaryExpression { operator, argument }`, `Identifier { name }`, `Literal { value }`

`alternate` is either a `BlockStatement` or `null`. Parentheses affect precedence but do not add an
AST node.

## 4. Language semantics

A block creates a child lexical environment. `let` defines only in the current environment and may
shadow an outer binding; defining the same name twice in one environment is a `RuntimeError`.
Assignment updates the nearest existing binding. Reading or assigning an undefined name is a
`RuntimeError`.

Values are finite numbers, strings, booleans, and `null`. Only `false` and `null` are falsey.
`and` and `or` short-circuit and return an operand value. `!` returns a boolean. Unary `-`, binary
`-`, `*`, `/`, and ordered comparisons require numbers; division by zero is a `RuntimeError`. `+`
accepts two numbers or two strings, never mixed values. Equality compares type and value without
coercion.

Statements yield values: declarations, prints, assignments, and expression statements yield their
expression; a non-empty block yields its final statement; an empty block yields `null`; `if` yields
the chosen branch or `null`; `while` yields its last body value or `null` if never entered. A program
yields its final statement or `null` when empty.

`print` appends one string: strings unchanged, `null` as `null`, booleans lowercase, and numbers via
JavaScript's canonical `String(number)` conversion. Enforce a default 100,000-step evaluation limit.
Each visited statement or expression consumes one tree-engine step. Parser-produced left-associative
binary and logical chains must be walked without recursive host calls; every node in such a chain
still consumes its own step.

## 5. Compiler and virtual machine

`compile(ast)` returns a fresh plain object:

```text
{ version: 1, constants: [...], code: [{ op, arg?, loc }, ...] }
```

Constants contain only language values. Code ends in exactly one `HALT`. Supported opcodes are
`CONSTANT`, `NULL`, `TRUE`, `FALSE`, `GET`, `DEFINE`, `SET`, `POP`, `PRINT`, `NEGATE`, `NOT`, `ADD`,
`SUBTRACT`, `MULTIPLY`, `DIVIDE`, `EQUAL`, `NOT_EQUAL`, `GREATER`, `GREATER_EQUAL`, `LESS`,
`LESS_EQUAL`, `JUMP`, `JUMP_IF_FALSE`, `ENTER_SCOPE`, `EXIT_SCOPE`, and `HALT`. Jump arguments are
absolute instruction indexes.

`runBytecode` must validate untrusted bytecode before execution: exact data-only record fields, dense
arrays without custom fields and with exactly the intrinsic `Array.prototype` (not a subclass,
null prototype, or custom prototype), version,
constant value types and finiteness, opcode names, required/forbidden arguments, integer in-range
indexes and targets, location shapes, final `HALT`, no early `HALT`, and statically safe stack/scope
depth on every reachable control-flow path. Joins must agree on stack and scope depth. Reject invalid
input with `BytecodeError`; the final `HALT` must be reachable, and validation must not partly execute
the program. Validation must not invoke inherited behavior from bytecode arrays. Runtime language
semantics match the tree interpreter. Each dispatched instruction consumes one VM step. Both engines
default to 100,000 steps, but `maxSteps` is an engine-local work budget: the same numeric budget need
not expire at the same source construct.

Compilation must handle parser-produced left-associative binary and logical chains iteratively rather
than rejecting an otherwise valid flat expression at an internal recursion threshold. Except for
engine-local step-budget exhaustion, compiled bytecode must produce exactly the same value, output,
errors by class/stage, scoping effects, and short-circuit behavior as the tree walker for every valid
source program under the applicable limits. At a step-budget boundary, each engine must either
return normally or raise a deterministic `RuntimeError`; cross-engine outcome parity is not required.

## 6. Errors

Language failures extend `LanguageError` and expose `stage`, `line`, and `column`: `LexError` uses
stage `lex`, `ParseError` uses `parse`, `RuntimeError` uses `runtime`, `CompileError` uses `compile`,
and `BytecodeError` uses `bytecode`. Messages are deterministic and must not include host paths or
JavaScript stack traces. Limit failures use the corresponding stage-specific class.

## 7. Completion criteria

Pass public tests plus learner-written coverage of every production, operator, error family, scope
rule, limit, and malformed bytecode category. Differentially execute representative terminating
programs through both engines. Passing public tests alone is not completion evidence.
