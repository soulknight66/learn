# Sprig language and tool contract

## 1. Source text

- Input is a regular byte stream whose language tokens are ASCII. Space, tab, carriage return, and newline are whitespace.
- `#` begins a comment through the next newline or end of file.
- Identifiers match `[A-Za-z_][A-Za-z0-9_]*` and contain at most 31 bytes.
- Integer literals are unsigned decimal spellings in the range `0` through `9223372036854775807`. A leading minus is a separate token.
- The whole source file is limited to 1 MiB by the supplied CLI.

## 2. Grammar

The notation uses `*` for repetition and `|` for choice.

```text
program        := statement* EOF
statement      := "let" IDENT "=" expression ";"
                | "print" expression ";"
expression     := term (("+" | "-") term)*
term           := unary (("*" | "/") unary)*
unary          := "-" unary | primary
primary        := INTEGER | IDENT | "(" expression ")"
```

Binary operators associate left-to-right. Unary minus binds more tightly than multiplication. Every declaration introduces one immutable binding; a name may not be redeclared, and a use must follow its declaration. The implementation limits a program to 64 bindings, 1024 emitted instructions, and 512 simultaneously nested parentheses/unary operators.

## 3. Compilation and execution

Compile to the opcodes declared in `starter/include/sprig.h`. `CONST n` pushes an immediate, `LOAD s` pushes slot `s`, `STORE s` pops into slot `s`, arithmetic pops right then left and pushes one result, `NEG` replaces the top value, `PRINT` pops and writes it, and `HALT` ends execution.

The VM stack holds at most 256 values. Arithmetic is exact signed 64-bit arithmetic: overflow, division by zero, and `INT64_MIN / -1` are runtime errors rather than C undefined behavior. A successful run exits 0 and prints each value as canonical decimal plus newline.

## 4. CLI and diagnostics

```text
sprig FILE
sprig --tokens FILE
sprig --disassemble FILE
```

- Normal mode compiles and executes.
- `--tokens` lexes only and prints one stable token record per line, including EOF.
- `--disassemble` compiles only and prints indexed instructions.
- Usage errors exit 64, lexical or compile errors 65, runtime errors 70, and file I/O or size failures 74.
- Diagnostics go to standard error, contain the source path and location, contain the word `error`, and leave standard output empty unless earlier `print` statements already executed before a runtime failure.

## 5. Completion criteria

The starter must build without warnings under its supplied flags. All public tests must pass without special-casing their inputs. Independent validation may exercise whitespace/comments, precedence, associativity, name resolution, every limit, malformed syntax, arithmetic boundaries, output channels, modes, and exit codes.
