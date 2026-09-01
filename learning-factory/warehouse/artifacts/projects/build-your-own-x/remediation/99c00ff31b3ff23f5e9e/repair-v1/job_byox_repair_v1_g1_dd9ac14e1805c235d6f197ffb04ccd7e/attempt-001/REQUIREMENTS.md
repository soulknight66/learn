# Mica language requirements

This document is the normative learner-visible contract. ASCII is used for
source spelling and diagnostics. Programs are deterministic and have no input.

## 1. Lexical grammar

Only the ASCII bytes space (`0x20`), horizontal tab (`0x09`), carriage return
(`0x0d`), and line feed (`0x0a`) are whitespace. Outside a line comment,
vertical tab (`0x0b`) and form feed (`0x0c`) are invalid bytes rather than
whitespace. A line comment starts with `//` and runs through the next line feed
or end of file. Keywords are `let`, `print`, `if`, `else`, and `while`.

Identifiers match `[A-Za-z_][A-Za-z0-9_]*` and are case-sensitive. An integer
literal is one or more decimal digits and must be in `0..9223372036854775807`.
There are no signs inside literals; unary `-` is an operator.

Single-character tokens are `(`, `)`, `{`, `}`, `;`, `+`, `-`, `*`, `/`, `%`,
`<`, `>`, and `=`. The two-character operators are `==`, `!=`, `<=`, and `>=`.
A lone `!` is invalid.

`tokens` writes `line:column KIND lexeme`, except integer tokens use their
canonical decimal value as the final field. `EOF` has `-` as that field. Token
positions are one-based and point to the first byte. A line feed advances the
line and resets the column to 1. Every other byte, including a horizontal tab
or carriage return, advances the column by exactly one. Thus positions do not
use display-width tab stops, and a carriage return does not start a new line.

## 2. Syntax

```ebnf
program     = statement*, EOF ;
statement   = "let", IDENT, "=", expression, ";"
            | IDENT, "=", expression, ";"
            | "print", expression, ";"
            | "if", "(", expression, ")", block, ("else", block)?
            | "while", "(", expression, ")", block ;
block       = "{", statement*, "}" ;
expression  = equality ;
equality    = comparison, (("==" | "!="), comparison)* ;
comparison  = term, (("<" | "<=" | ">" | ">="), term)* ;
term        = factor, (("+" | "-"), factor)* ;
factor      = unary, (("*" | "/" | "%"), unary)* ;
unary       = ("+" | "-"), unary | primary ;
primary     = INTEGER | IDENT | "(", expression, ")" ;
```

Binary operators at a grammar level associate left-to-right. A block is only
valid as part of `if` or `while`; it does not create a variable scope.

## 3. Static rules

- A `let` declaration introduces a name for all following source positions,
  including statements nested later in the same program.
- A name must be declared before any read or assignment.
- Redeclaring a name anywhere in the program is an error.
- At most 256 variables and 65,536 AST nodes are allowed.
- Source size is at most 1,048,576 bytes, including comments and whitespace.
- Syntactic nesting or resulting expression-tree depth beyond 128 levels is
  rejected.

Validation occurs after parsing and before execution or assembly emission. It
walks statements in source order. An `if` branch declaration is therefore
visible after that branch in source order even when the branch does not execute;
learners may instead reject declarations inside control flow as a documented
extension, but the public contract above is the target.

## 4. Runtime semantics

Values are signed 64-bit integers. Arithmetic wraps modulo 2^64 and is then
interpreted as a signed two's-complement value. This wrap is language behavior,
not C signed-overflow behavior. Comparisons yield exactly `0` or `1` and use
signed ordering. Zero is false; every nonzero value is true.

Division truncates toward zero. Division or remainder by zero is a runtime
error. The pair `INT64_MIN / -1` wraps to `INT64_MIN`; its remainder is zero.

`let x = e;` evaluates `e` and stores it in `x`. Assignment updates a declared
name. `print e;` writes the signed decimal value followed by `\n`. `if` evaluates
only its selected branch. `while` reevaluates its condition and body, with a
shared execution budget of 10,000,000 statement visits; exceeding it is a
runtime error. All storage slots start at zero, so a declaration made statically
visible by an unexecuted branch retains zero until its declaration statement or
an assignment actually runs.

## 5. CLI, output, and failure behavior

The three accepted forms are:

```text
mica tokens FILE
mica run FILE
mica compile FILE -o FILE
```

Success returns status 0. Usage, I/O, lexical, parse, validation, and runtime
failures return nonzero and write one line to stderr beginning with
`mica: <phase> error:`. Normal program output must never be written on stderr.

Compiled assembly follows the x86-64 System V ABI and must link with `cc -no-pie`.
The linked program returns 0 on success, reports division by zero to stderr, and
returns nonzero for that error. Its stdout must equal interpreter stdout for all
valid terminating programs within the stated resource limits.
