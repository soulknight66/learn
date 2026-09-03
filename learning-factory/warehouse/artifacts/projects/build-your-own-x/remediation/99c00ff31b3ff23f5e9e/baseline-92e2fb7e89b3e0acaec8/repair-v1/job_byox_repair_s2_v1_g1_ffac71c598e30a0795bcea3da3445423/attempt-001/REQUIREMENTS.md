# Pebble language requirements

## 1. Source and lexical rules

- Input is UTF-8 bytes, but tokens use ASCII letters, digits, and punctuation.
- A source file is at most 1,048,576 bytes.
- Spaces, tabs, carriage returns, and newlines separate tokens.
- `#` begins a comment extending through the next newline or end of file.
- Identifiers match `[A-Za-z_][A-Za-z0-9_]*` and are case-sensitive.
- Decimal integer literals must fit in `0..9223372036854775807`.
- Keywords are `let`, `print`, `if`, `else`, and `while`.

Every lexical or syntax diagnostic must include a 1-based `line:column` and
exit with status 65. Reading or writing failure exits 66; this includes a
failed standard-output write or flush in either backend. Bad CLI usage exits
64; evaluation failures exit 70.

## 2. Grammar

```text
program        := declaration* statement* EOF
declaration    := "let" IDENT "=" expression ";"
statement      := IDENT "=" expression ";"
                | "print" expression ";"
                | "if" expression block ("else" block)?
                | "while" expression block
block          := "{" statement* "}"
expression     := equality
equality       := comparison (("==" | "!=") comparison)*
comparison     := term (("<" | "<=" | ">" | ">=") term)*
term           := factor (("+" | "-") factor)*
factor         := unary (("*" | "/" | "%") unary)*
unary          := ("-" | "!") unary | primary
primary        := INTEGER | IDENT | "(" expression ")"
```

Declarations are legal only at the start of the outermost program. A name must
be declared exactly once, and its initializer may use only earlier
declarations. Assignment and reads require an existing declaration. Reject
more than 256 variables, blocks nested beyond 128 levels, or an expression tree
deeper than 128 levels. Parsing must separately cap nested unary/parenthesis
constructs at 128 so hostile syntax cannot create unbounded parser recursion.
If a repeated declaration also has an invalid initializer, diagnose the
duplicate name first; otherwise resolve the initializer before installing the
new name, so a declaration cannot refer to itself.

## 3. Semantics

- Values are signed 64-bit integers. Comparisons and logical negation produce
  exactly `0` or `1`; zero is false and every nonzero value is true.
- Operators of equal precedence associate left-to-right.
- `print` writes one base-10 integer and a newline to standard output.
- Signed division truncates toward zero. Remainder satisfies
  `a == (a / b) * b + (a % b)` and has the dividend's sign when nonzero.
  Addition, subtraction, multiplication, and unary negation must detect
  overflow. For both `/` and `%`, the operand pair `INT64_MIN, -1` is defined
  as arithmetic overflow; division or remainder by zero is also an error.
  These runtime failures print a stable `runtime error:` diagnostic to
  standard error and exit 70.
- `eval` accepts `--max-steps N`, where `N` is in `1..1000000000`; the default
  is 1,000,000. Each non-loop statement execution and every loop-condition
  evaluation consumes one step. Exhaustion is a runtime error.

## 4. Compiler target

`compile INPUT -o OUTPUT` emits textual GNU/AT&T x86-64 assembly for the System
V AMD64 ABI. Linking the output with the host `cc` must produce a program whose
standard output, standard error, and exit status agree with `eval`, except that
compiled programs always use the default 1,000,000-step limit. The emitted
assembly may call the C library for formatted output and error reporting.

The compiler must fail before writing a successful output when static name
resolution fails. It should write through a temporary sibling file and rename
only after successful generation, so a failed compile does not masquerade as a
complete artifact.

## 5. Resource ownership

All opened files and allocated AST/list storage must be released on ordinary
success and handled coherently on error. Test drivers must use argv arrays,
isolated temporary directories, and bounded subprocess timeouts. Every child
must start in its own process group/session; timeout cleanup must signal that
entire group with a bounded TERM-to-KILL escalation. Retained standard output
and standard error must each be capped at 65,536 bytes.
