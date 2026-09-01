# Mini-C language and interpreter requirements

This document is normative. “Must” statements are observable requirements; examples are
illustrative. The accepted language is named Mini-C and is intentionally not ISO C.

## 1. Command-line contract

The executable must accept:

```text
minic [--max-steps N] SOURCE
```

`SOURCE` is a regular source file. `N` is a positive decimal integer. The default instruction
budget is 1,000,000. No other option or positional argument is accepted.

- Exit `0`: source compiled and `main()` returned normally.
- Exit `64`: command-line usage error.
- Exit `65`: source, lexical, name-resolution, or syntax error.
- Exit `66`: source file could not be opened or read.
- Exit `70`: runtime error, including arithmetic faults, stack/frame exhaustion, or step limit.

Diagnostics must go to standard error and include `SOURCE:line:` when tied to source. Language
output goes only to standard output. A successful program's `main` return value is not the host
process exit code.

## 2. Translation limits

Implementations must safely accept at least these sizes and must reject larger internal needs
with a diagnostic rather than corrupting memory:

| Resource | Required capacity |
|---|---:|
| source bytes | 1,048,576 |
| tokens | 65,536 |
| bytecode instructions | 65,536 |
| functions | 128 |
| parameters per function | 32 |
| locals, including parameters, per function | 256 |
| identifier bytes | 63 |
| operand values | 8,192 |
| active function frames | 256 |

The reference profile uses signed 64-bit values. Decimal literals range from `0` through
`9223372036854775807`.

## 3. Lexical grammar

Whitespace separates tokens. Both `//` line comments and non-nesting `/* ... */` comments are
ignored. An unterminated block comment is an error at the opening line.

Identifiers match `[A-Za-z_][A-Za-z0-9_]*`. Reserved words are `int`, `if`, `else`, `while`,
`return`, and `print`. Decimal integers have one or more digits. The operators are:

```text
+ - * / % ! = == != < <= > >= && ||
```

Punctuation is `(`, `)`, `{`, `}`, `,`, and `;`. Every other byte is invalid. There are no
strings, characters, pointers, arrays, preprocessors, structs, globals, or prototypes.

## 4. Concrete grammar

The notation uses `*`, `?`, and parentheses as EBNF operators; quoted text is literal.

```text
program       = function* EOF ;
function      = "int" IDENT "(" parameters? ")" block ;
parameters    = parameter ("," parameter)* ;
parameter     = "int" IDENT ;
block         = "{" statement* "}" ;
statement     = block
              | "int" IDENT ("=" expression)? ";"
              | IDENT "=" expression ";"
              | "if" "(" expression ")" statement ("else" statement)?
              | "while" "(" expression ")" statement
              | "return" expression ";"
              | "print" "(" expression ")" ";"
              | expression ";" ;
expression    = logical_or ;
logical_or    = logical_and ("||" logical_and)* ;
logical_and   = equality ("&&" equality)* ;
equality      = comparison (("==" | "!=") comparison)* ;
comparison    = term (("<" | "<=" | ">" | ">=") term)* ;
term          = factor (("+" | "-") factor)* ;
factor        = unary (("*" | "/" | "%") unary)* ;
unary         = ("!" | "-") unary | primary ;
primary       = INTEGER
              | IDENT
              | IDENT "(" arguments? ")"
              | "(" expression ")" ;
arguments     = expression ("," expression)* ;
```

An assignment is a statement, not an expression. Function bodies and nested blocks share one
function-local namespace: shadowing is forbidden, and every declared name must be unique in its
function. A name must be declared before its use. Functions may be called before their
definitions, but duplicate or undefined functions are errors. Exactly one zero-argument
function named `main` is required.

## 5. Evaluation semantics

- Values are signed 64-bit integers. False is zero; true is one.
- Comparisons, equality, and `!` produce exactly zero or one.
- `&&` and `||` evaluate left to right, short-circuit, and produce zero or one.
- Other binary operands evaluate left to right.
- Arithmetic that cannot be represented in signed 64 bits is a runtime error. This includes
  negating the minimum value and dividing it by `-1`.
- Division truncates toward zero. Remainder follows C11 signed remainder semantics. Division or
  remainder by zero is a runtime error.
- Locals without an initializer start at zero. Arguments are passed by value.
- `print(x);` writes the base-10 value followed by one newline.
- Reaching the closing brace of a function is equivalent to `return 0;`.
- A `while` condition is reevaluated for every iteration.

Every executed bytecode instruction consumes one step, including jumps, calls, and returns.
Execution must stop before executing instruction `N + 1` under `--max-steps N`.

## 6. Required milestones

1. Safe source loading and stable diagnostics.
2. Complete lexer with comment and integer-boundary handling.
3. Precedence parser/compiler with forward-call resolution.
4. Bounded bytecode VM with checked arithmetic and call frames.
5. Black-box negative tests and deterministic step limiting.
6. Staged bootstrap: run a Mini-C program that implements an interpreter for a documented
   integer bytecode and verify that its guest program prints `42`.

The bootstrap must not use a host `eval` escape hatch or special-case the fixture. Its interpreter
loop, dispatch, program representation, and stack operations must execute as ordinary Mini-C.
