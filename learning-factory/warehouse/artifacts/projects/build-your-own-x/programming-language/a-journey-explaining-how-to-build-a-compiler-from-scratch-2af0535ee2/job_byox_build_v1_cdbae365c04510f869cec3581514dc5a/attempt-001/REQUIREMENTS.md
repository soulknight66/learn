# Pebble requirements

## 1. Lexical rules

- Source is UTF-8 bytes, but language identifiers are ASCII only: `[A-Za-z_][A-Za-z0-9_]*`.
- Decimal integer literals contain one or more ASCII digits and must fit `0..INT64_MAX`.
- Spaces, tabs, carriage returns, and newlines separate tokens. `//` comments end at newline.
- Keywords are `let`, `print`, `if`, `else`, and `while` and must match as whole identifiers.
- Punctuation is `(` `)` `{` `}` `;`; operators are `+ - * / % ! = < > <= >= == != && ||`.
- A lone `&` or `|`, an unknown byte, and an out-of-range literal are compile errors.

## 2. Grammar

The notation `{x}` means repetition and `[x]` means optional content.

```text
program     := { declaration } EOF
declaration := "let" IDENT "=" expression ";" | statement
statement   := "print" expression ";"
             | IDENT "=" expression ";"
             | "if" "(" expression ")" block [ "else" block ]
             | "while" "(" expression ")" block
             | block
block       := "{" { declaration } "}"
expression  := logical_or
logical_or  := logical_and { "||" logical_and }
logical_and := equality { "&&" equality }
equality    := comparison { ("==" | "!=") comparison }
comparison  := term { ("<" | "<=" | ">" | ">=") term }
term        := factor { ("+" | "-") factor }
factor      := unary { ("*" | "/" | "%") unary }
unary       := ("!" | "-") unary | primary
primary     := INTEGER | IDENT | "(" expression ")"
```

Declarations are visible only after their initializer. Redeclaring a name in the same block is an
error; nested blocks may shadow it. Reads and assignments resolve the nearest enclosing declaration.
An unresolved name is a compile error. An `else` binds to its immediately preceding `if` because both
branches are braced blocks.

## 3. Semantics

- Values are signed 64-bit integers. Comparisons, equality, and logical operators produce exactly `0`
  or `1`. `!x` is `1` only when `x == 0`.
- `&&` and `||` evaluate left to right and short-circuit the right operand.
- `print e;` writes the base-10 value followed by one newline.
- Arithmetic overflow, division or remainder by zero, and `INT64_MIN / -1` are runtime errors. Unary
  negation of `INT64_MIN` is also a runtime error. Do not rely on signed C overflow.
- Statements execute in source order. A loop condition is evaluated before each iteration.
- A successful empty program is valid and has no output.

## 4. Public C API

`starter/include/pebble.h` is normative. Compilation must create an immutable `PebbleProgram` or fail
without publishing a partial object. Execution may be repeated on a compiled program. All owned memory
must be released by `pebble_program_free`. A null options pointer selects documented defaults. Output
and diagnostics go only to the caller-provided streams.

The implementation must return `PEBBLE_COMPILE_ERROR` for lexical, syntax, and name errors;
`PEBBLE_RUNTIME_ERROR` for arithmetic faults or malformed internal execution state;
`PEBBLE_LIMIT_ERROR` for configured code, symbol, stack, or execution-step limits; and
`PEBBLE_SYSTEM_ERROR` for allocation or invalid API arguments. Diagnostics use
`<line>:<column>: <message>\n` when tied to source, and must contain no pointer values.

## 5. CLI

`pebble FILE` reads one regular input path; `pebble -e SOURCE` runs a supplied string. Any other
arguments print a one-line usage diagnostic. Exit statuses are 0 on success, 64 for usage, 65 for a
compile error, 70 for runtime or limit errors, and 74 for input/system errors. Source diagnostics go
to stderr; language output goes to stdout. The CLI must reject an input larger than 1 MiB before
compilation.

## 6. Resource and quality constraints

Defaults are at most 65,536 bytecode instructions, 4,096 constants, 1,024 symbol slots, 1,024 VM stack
values, and 1,000,000 executed instructions. User-set nonzero limits replace defaults. Size arithmetic
must be checked. Each run owns all mutable VM state; the compiled object must not hold `FILE *` values.
Build cleanly as C11 with the warning flags in the supplied Makefile.
