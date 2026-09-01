# Minnow requirements

This document is normative. Keywords and byte sequences shown in code font are exact. A conforming
implementation exposes the Python API and CLI described below and must reject malformed input rather
than guessing.

## 1. Source language

Source is Unicode text, but identifiers and decimal digits are ASCII-only. Spaces, tabs, carriage
returns, and line feeds are whitespace. `//` starts a comment that runs through the next line ending or
end of input. Source positions are one-based; CRLF is one line ending.

Identifiers match `[A-Za-z_][A-Za-z0-9_]*`. The reserved words are `let`, `print`, `if`, `else`,
`while`, `true`, and `false`. Integer literals are one or more ASCII digits and must be no larger than
9,223,372,036,854,775,807. There are no strings, implicit semicolons, or nested comments.

Operators and punctuation are:

```text
+  -  *  /  %  !  ==  !=  <  <=  >  >=  =  ;  (  )  {  }
```

When two tokens share a prefix, take the longest valid token. A lone unexpected character, including
an unsupported non-ASCII letter or digit, is a lexical error.

The grammar is:

```text
program     := statement* EOF ;
statement   := "let" IDENT "=" expression ";"
             | IDENT "=" expression ";"
             | "print" expression ";"
             | "if" "(" expression ")" block ("else" block)?
             | "while" "(" expression ")" block ;
block       := "{" statement* "}" ;
expression  := equality ;
equality    := comparison (("==" | "!=") comparison)* ;
comparison  := term (("<" | "<=" | ">" | ">=") term)* ;
term        := factor (("+" | "-") factor)* ;
factor      := unary (("*" | "/" | "%") unary)* ;
unary       := ("!" | "-") unary | primary ;
primary     := INT | "true" | "false" | IDENT | "(" expression ")" ;
```

Binary operators are left-associative. Unary operators associate right. Missing delimiters, trailing
tokens, and an `else` without its preceding `if` are syntax errors.

## 2. Static meaning

The program and each block introduce lexical scopes. `let` creates a new local in the current scope;
declaring the same name twice in that scope is an error, while shadowing an outer declaration is legal.
The initializer is resolved before the new declaration becomes visible. Thus, `let x = x;` uses an
outer `x` if one exists and is otherwise an undefined-name error.

Every read and assignment must resolve to the nearest enclosing declaration. Assignment changes that
declaration; it never creates a name. Locals need not remain addressable after their scope closes, but
the bytecode header records the total slot count chosen by the compiler, at most 65,535.

Expressions evaluate left operand before right operand. `if` and `while` treat zero as false and every
other value as true. `true` is integer 1 and `false` is integer 0. `!x` is 1 when `x` is zero, otherwise
0. Comparisons and equality produce exactly 0 or 1. `print` writes the signed decimal representation
followed by `\n`.

Values are signed 64-bit integers. Addition, subtraction, multiplication, negation, division, and
remainder are checked. An out-of-range result is a runtime error. Division truncates toward zero;
remainder is `a - trunc(a / b) * b`. Division or remainder by zero is a runtime error, as is
`-9223372036854775808 / -1`. Source literals themselves are limited to the nonnegative maximum, so the
minimum signed value can arise only through a calculation.

## 3. MNO1 binary format

The compiled file is a 10-byte header followed by a code section. Multi-byte fields are big-endian.

| Offset | Width | Meaning |
| ---: | ---: | --- |
| 0 | 4 | ASCII magic `MNO1` |
| 4 | 2 | unsigned local-slot count |
| 6 | 4 | unsigned code-section byte length |
| 10 | variable | instruction bytes |

The declared length must equal the remaining file length. No trailing bytes are allowed. Instruction
addresses and jump operands are zero-based byte offsets within the code section, never file offsets.

| Byte | Mnemonic | Operand | Stack effect | Meaning |
| ---: | --- | --- | --- | --- |
| `0x01` | `CONST` | signed i64 | `+1` | push operand |
| `0x02` | `LOAD` | unsigned u16 | `+1` | push local |
| `0x03` | `STORE` | unsigned u16 | `-1` | pop into local |
| `0x10` | `ADD` | none | `-1` | checked `a + b` |
| `0x11` | `SUB` | none | `-1` | checked `a - b` |
| `0x12` | `MUL` | none | `-1` | checked `a * b` |
| `0x13` | `DIV` | none | `-1` | checked truncating division |
| `0x14` | `MOD` | none | `-1` | checked remainder |
| `0x15` | `NEG` | none | `0` | checked negation |
| `0x16` | `NOT` | none | `0` | logical negation |
| `0x20` | `EQ` | none | `-1` | equality |
| `0x21` | `NE` | none | `-1` | inequality |
| `0x22` | `LT` | none | `-1` | less than |
| `0x23` | `LE` | none | `-1` | less or equal |
| `0x24` | `GT` | none | `-1` | greater than |
| `0x25` | `GE` | none | `-1` | greater or equal |
| `0x30` | `PRINT` | none | `-1` | emit top value |
| `0x40` | `JUMP` | unsigned u32 | `0` | unconditional branch |
| `0x41` | `JUMP_IF_FALSE` | unsigned u32 | `-1` | pop and branch if zero |
| `0xff` | `HALT` | none | `0` | stop successfully |

For a binary operation the VM pops `b`, then `a`, and computes `a op b`. Local slots begin initialized
to zero, though a conforming compiler never reads a declaration before its initializer has stored it.

Before execution, decode the whole code section and reject:

- unknown or truncated instructions;
- slot operands outside the header's slot count;
- jumps outside the code section or into an operand;
- stack underflow, inconsistent stack depth at a control-flow merge, or depth above 65,535;
- unreachable instructions;
- no final `HALT`, any `HALT` before the final instruction, a reachable fall-through past the code,
  or a nonempty stack at `HALT`.

Validation must finish before an instruction executes or output is written.

## 4. Python API

Package `minnow` must export:

```python
compile_source(source: str) -> bytes
run_bytecode(program: bytes, stdout: TextIO, *, step_limit: int = 1_000_000) -> None
run_source(source: str, stdout: TextIO, *, step_limit: int = 1_000_000) -> None
MiniError
LexError
ParseError
SemanticError
FormatError
RuntimeFault
StepLimitExceeded
```

`source` must be `str`, bytecode must be `bytes` or `bytearray`, and `step_limit` must be a positive
integer (booleans do not count as integers). Contract violations raise `TypeError` or `ValueError`.
Language and machine failures use the exception classes above. `run_source` is compile then run.

Source errors expose integer `.line` and `.column` attributes and a stable `.code` beginning `LEX`,
`PARSE`, or `SEM`. Machine errors expose a stable `.code` beginning `FORMAT`, `RUNTIME`, or `LIMIT`.
Exact English wording is not part of the contract.

## 5. CLI

`python3 -m minnow` supports:

```text
minnow compile SOURCE OUTPUT
minnow run [--max-steps N] BYTECODE
minnow exec [--max-steps N] SOURCE
```

Text is read as strict UTF-8; bytecode is binary. A successful command exits 0. Usage, I/O, decoding,
compile, format, runtime, and limit failures print one concise diagnostic to standard error, produce no
traceback, and exit 2. `compile` must not leave a newly created or partially overwritten output file if
compilation or writing fails. `run` and `exec` write program output to standard output.
