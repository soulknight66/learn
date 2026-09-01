# Mica language requirements

This document is normative. Keywords and identifiers are case-sensitive.

## 1. Source and tokens

- Input is a UTF-8-compatible byte stream whose language tokens are ASCII.
- Space, tab, carriage return, and line feed are whitespace.
- `#` starts a comment through the next line feed or end of file.
- An identifier matches `[A-Za-z_][A-Za-z0-9_]*`.
- An integer literal is one or more decimal digits and must be at most
  `1000000000` before unary operators are applied.
- Keywords are `let`, `print`, `if`, `else`, `while`, `halt`, `true`, and `false`.
- Punctuation/operators are `(`, `)`, `{`, `}`, `;`, `=`, `+`, `-`, `*`, `/`,
  `%`, `!`, `==`, `!=`, `<`, `<=`, `>`, and `>=`.
- Any other non-whitespace byte is a lexical error.

Locations are one-based. A token's location is its first byte. A lexical error
for an unknown byte reports that byte; an oversized integer reports its first
digit. Newlines are line feeds; a preceding carriage return counts as whitespace.

## 2. Grammar

```text
program     := statement* EOF ;
statement   := "let" IDENT "=" expression ";"
             | IDENT "=" expression ";"
             | "print" expression ";"
             | "if" expression block ("else" block)?
             | "while" expression block
             | "halt" ";" ;
block       := "{" statement* "}" ;
expression  := equality ;
equality    := comparison (("==" | "!=") comparison)* ;
comparison  := term (("<" | "<=" | ">" | ">=") term)* ;
term        := factor (("+" | "-") factor)* ;
factor      := unary (("*" | "/" | "%") unary)* ;
unary       := ("!" | "-") unary | primary ;
primary     := INTEGER | "true" | "false" | IDENT
             | "(" expression ")" ;
```

Binary operators at the same level associate left-to-right. Unary operators
associate right-to-left. A semicolon is not used after an `if` or `while` block.
An `else` binds to the immediately preceding `if` because bodies are explicit
blocks.

## 3. Names and values

All values are signed `Int64` integers. `false` compiles to `0`, `true` to `1`,
and truth tests treat zero as false and every other value as true.

Mica has one program-wide variable scope, including inside blocks. `let` creates
one slot and is an error if that spelling was declared earlier anywhere in the
program. An initializer is compiled before its name becomes visible, so
`let x = x;` is invalid unless an earlier `x` exists (which would make the new
declaration a redeclaration anyway). Reading or assigning an undeclared name is a
compile error. Names are resolved before execution, even in unreachable code.
Every allocated slot initially contains zero; reaching its `let` statement
evaluates the initializer and replaces that value. This defines reads after a
declaration whose control-flow path did not execute.

## 4. Evaluation and bytecode

The compiler emits stack-machine instructions. A conforming implementation must
support constants, slot loads/stores, arithmetic, comparisons, unary operations,
conditional and unconditional jumps, printing, and halting. The exact Pascal
representation is not prescribed. Jump targets are zero-based instruction
indices. Conditional jump consumes its condition.

- `+`, `-`, `*`, unary `-`, `/`, and `%` produce integer values.
- Division truncates toward zero. Remainder is consistent with that quotient:
  `a = (a / b) * b + (a % b)`.
- Division or remainder by zero is a runtime error.
- Every arithmetic result must be in `[-1000000000, 1000000000]`; otherwise it is
  a runtime error. Operands are already in this domain.
- Comparisons and equality produce exactly `0` or `1`.
- `!x` produces `1` when `x = 0`, otherwise `0`.
- `print` consumes its value and writes its base-ten representation plus `LF`.
- `halt;` stops immediately. Falling off the program is equivalent to an implicit
  halt.
- At most 100000 bytecode instructions may execute. Attempting instruction
  100001 is a runtime error. This makes all test runs bounded.

No output written before a runtime error is rolled back.

## 5. Command-line contract

```text
mica SOURCE
mica --tokens SOURCE
mica --bytecode SOURCE
```

Default mode tokenizes, compiles, and runs. `--tokens` prints a deterministic
token listing and does not compile. `--bytecode` compiles and prints a
deterministic instruction listing without running. These listings are useful for
debugging; their required format is documented in `starter/README.md`.

The executable writes program output/listings only to standard output. It writes
one diagnostic to standard error on failure:

```text
SOURCE:LINE:COLUMN: PHASE: MESSAGE
```

`PHASE` is `lex`, `parse`, `compile`, or `runtime`. Exact message wording is not
normative, but phase and location are. Usage errors may omit a source location.

Exit status is 0 for success, 64 for command usage, 65 for lexical/parse/compile
failure, 66 when the source cannot be read, and 70 for runtime failure.

## 6. Acceptance examples

```text
let n = 5;
let acc = 1;
while n > 1 {
  acc = acc * n;
  n = n - 1;
}
print acc;
```

prints `120`. The expression `20 / 3 * 3 + 20 % 3` prints `20`. The program
`print 1 / 0;` fails in phase `runtime` with exit status 70.
