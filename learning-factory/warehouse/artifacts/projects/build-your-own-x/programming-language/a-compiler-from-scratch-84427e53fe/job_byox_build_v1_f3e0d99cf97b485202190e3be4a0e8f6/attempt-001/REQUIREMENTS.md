# Pebble language contract

## Public Ruby API

All code lives in module `Pebble` and is loaded by `require "pebble"`.

- `Lexer.new(source).scan_tokens` returns an array of `Token` objects ending in exactly one `EOF`.
- `Parser.new(tokens).parse` returns a program AST.
- `Compiler.new.compile(ast)` returns a `Program` with `instructions` and `local_count`.
- `VM.new(program, output: io, max_steps: 100_000).run` executes and returns `nil`.
- `Pebble.compile(source)` performs lexing, parsing, and compilation.
- `Pebble.run(source, output: io, max_steps: 100_000)` compiles, executes, and returns `nil`.

`LexError`, `ParseError`, `CompileError`, and `VMError` inherit from `Pebble::Error`. Diagnostics must include a one-based `line:column` location for source errors. Exact prose is not otherwise prescribed.

## Lexical grammar

Identifiers match `[A-Za-z_][A-Za-z0-9_]*` and are case-sensitive. Decimal integer literals match `0|[1-9][0-9]*`; a leading-zero sequence such as `01` is a lexical error. Integers must be in `0..2_147_483_647` before unary negation. Spaces, tabs, carriage returns, and newlines separate tokens. `//` starts a comment through the next newline or end of input.

Keywords are `let`, `print`, `if`, `else`, `while`, `true`, and `false`. Operators and punctuation are:

```text
+ - * / % ! = == != < <= > >= ( ) { } ;
```

The two-character forms use longest match. Each `Token` has `type`, original `lexeme`, decoded `literal` (only integers and booleans; otherwise `nil`), and the starting `line` and `column`. Token types are uppercase symbols such as `:LET`, `:IDENTIFIER`, `:INTEGER`, `:EQUAL_EQUAL`, and `:EOF`.

## Syntax

The grammar is unambiguous; `*` means repetition and `?` means optional.

```ebnf
program     = statement* EOF ;
statement   = "let" IDENTIFIER "=" expression ";"
            | IDENTIFIER "=" expression ";"
            | "print" expression ";"
            | "if" "(" expression ")" block ("else" block)?
            | "while" "(" expression ")" block ;
block       = "{" statement* "}" ;
expression  = equality ;
equality    = comparison (("==" | "!=") comparison)* ;
comparison  = term (("<" | "<=" | ">" | ">=") term)* ;
term        = factor (("+" | "-") factor)* ;
factor      = unary (("*" | "/" | "%") unary)* ;
unary       = ("!" | "-") unary | primary ;
primary     = INTEGER | "true" | "false" | IDENTIFIER
            | "(" expression ")" ;
```

Blocks are required after `if`, `else`, and `while`. A bare block is not a statement. Empty programs and empty blocks are valid. There is no automatic semicolon insertion. Parsing consumes the entire token stream; trailing junk is an error.

## Required AST schema

AST nodes are hashes with symbol keys. A program is `{ type: :program, statements: [...] }`. Statements use these shapes:

```ruby
{ type: :let, name: "x", value: expression, token: token }
{ type: :assign, name: "x", value: expression, token: token }
{ type: :print, value: expression, token: token }
{ type: :if, condition: expression, then_body: [...], else_body: [...], token: token }
{ type: :while, condition: expression, body: [...], token: token }
```

Expressions are `:literal` (`value`, `token`), `:variable` (`name`, `token`), `:unary` (`operator`, `operand`, `token`), or `:binary` (`operator`, `left`, `right`, `token`). Operator values are token-type symbols.

## Static name rules

`let` introduces a variable in the current lexical scope. Redeclaring a name in the same scope is a `CompileError`; shadowing in a nested block is valid. A variable is visible only after its initializer has compiled, so `let x = x + 1;` does not refer to the new `x` (it may refer to an outer `x`). Reads or assignments with no visible declaration are compile errors.

The bodies of `if`, `else`, and `while` are separate nested scopes. Locals may be represented by numeric slots. Slot allocation and bytecode output must be deterministic for identical source.

## Values and execution

Pebble has exactly two runtime value types: 32-bit signed integers and booleans. Ruby's `Integer` and `TrueClass`/`FalseClass` represent them, but booleans must never count as integers.

- `+ - * / %` and unary `-` require integers.
- `< <= > >=` require integers and return booleans.
- `==` and `!=` accept any Pebble values; values of different Pebble types are unequal.
- `!`, and conditions for `if` and `while`, require booleans. There is no truthiness.
- Arithmetic results must remain in `-2_147_483_648..2_147_483_647`; otherwise raise `VMError`.
- Division truncates toward zero. Modulo is defined by `a - truncate_toward_zero(a / b) * b`, so its sign follows the dividend. Division or modulo by zero raises `VMError`.
- `print` writes lowercase `true`/`false` or a base-10 integer followed by `\n` to the supplied output object.

The VM raises `VMError` on malformed instructions, invalid operands or targets, stack underflow, invalid local access, execution without `HALT`, or exceeding `max_steps`. A positive integer step budget is required. A source-compiled program ends in one `HALT`, has no unresolved jump operands, leaves no expression values on the stack, and reports enough `local_count` storage for every emitted slot.

## Bytecode interface

Each instruction is an array whose first item is one of these symbols:

```text
CONST LOAD STORE ADD SUB MUL DIV MOD NEG NOT
EQ NE LT LE GT GE PRINT JUMP JUMP_IF_FALSE HALT
```

`CONST`, `LOAD`, `STORE`, `JUMP`, and `JUMP_IF_FALSE` have exactly one operand; all others have none. Jump targets are zero-based instruction indexes. `STORE`, `PRINT`, and `JUMP_IF_FALSE` consume their value. Binary operators consume right then left and push one result. `JUMP_IF_FALSE` accepts only a boolean and jumps only when it is false.

## Command-line behavior

`ruby starter/bin/pebble FILE` runs one UTF-8 source file and writes program output to stdout. It accepts exactly one argument. Usage or language errors are written to stderr and exit nonzero; a successful run exits zero. The CLI must not evaluate Ruby, spawn subprocesses, or access the network.
