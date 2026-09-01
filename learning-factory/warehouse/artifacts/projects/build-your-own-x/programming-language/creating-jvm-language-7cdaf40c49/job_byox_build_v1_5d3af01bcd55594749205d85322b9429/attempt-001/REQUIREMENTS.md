# Sprig compiler requirements

This file is normative. A conforming implementation is a deterministic Java 17+
library that compiles one Sprig program to one JVM class-file byte array.

## 1. Public API

Implement these starter types without changing their public signatures:

```java
CompilationResult SprigCompiler.compile(String source, String className)
```

`CompilationResult` contains either non-empty class bytes and no diagnostics, or
no class bytes and one or more diagnostics. User input errors must not escape as
uncaught exceptions. Calling `classBytes()` must return a defensive copy.
Both arguments are required; passing Java `null` is API misuse and throws
`NullPointerException` rather than producing a source diagnostic.

Each diagnostic has a stable `code`, a one-based `line` and `column`, and a
human-readable `message`. Diagnostics are ordered by source position, then code.
Required codes are listed below. The compiler may stop after the first syntax
error, but must be deterministic.

`className` must match `[A-Za-z_$][A-Za-z0-9_$]{0,127}`. Otherwise report
`E_CLASS_NAME` at `1:1`. The generated class uses the default package.

## 2. Lexical grammar

Source is Unicode text, but identifiers and digits are deliberately ASCII:

```text
identifier  := [A-Za-z_][A-Za-z0-9_]*
integer     := 0 | [1-9][0-9]*
lineComment := // characters until LF, CRLF, CR, or end of input
whitespace  := space | tab | LF | CRLF | CR
```

Keywords are `fn`, `main`, `Int`, `Bool`, `let`, `print`, `if`, `else`, `while`,
`return`, `true`, and `false`. Operators and punctuation are `(`, `)`, `{`, `}`,
`;`, `=`, `+`, `-`, `*`, `/`, `%`, `!`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `&&`,
`||`, and `->`. A lone `&` or `|` is invalid.

Token positions point to the first character. CRLF counts as one newline.
Unexpected characters produce `E_CHAR`. Integer text outside signed 32-bit
positive literal range (`0..2147483647`) produces `E_INT_RANGE`.

## 3. Syntax

The complete grammar is:

```text
program     := "fn" "main" "(" ")" "->" "Int" block EOF
block       := "{" statement* "}"
statement   := "let" identifier "=" expression ";"
             | identifier "=" expression ";"
             | "print" expression ";"
             | "if" "(" expression ")" block "else" block
             | "while" "(" expression ")" block
             | "return" expression ";"
expression  := or
or          := and ("||" and)*
and         := equality ("&&" equality)*
equality    := relation (("==" | "!=") relation)*
relation    := term (("<" | "<=" | ">" | ">=") term)*
term        := factor (("+" | "-") factor)*
factor      := unary (("*" | "/" | "%") unary)*
unary       := ("!" | "-") unary | primary
primary     := integer | "true" | "false" | identifier
             | "(" expression ")"
```

`->` is two adjacent characters and is otherwise invalid. Missing or unexpected
tokens produce `E_SYNTAX` at the current token. Trailing input is an error.

## 4. Static semantics

There are two source types, `Int` and `Bool`. Literals have their evident types.
Arithmetic and relational operands are `Int`; relational results are `Bool`.
`!`, `&&`, and `||` consume `Bool`. Equality requires matching operand types and
returns `Bool`. There are no conversions.

`let` declares a function-scoped, mutable local. Shadowing and redeclaration are
forbidden (`E_DUPLICATE`). A declaration becomes visible only after its
initializer, so `let x = x + 1;` reports `E_UNDECLARED` unless `x` was already
declared—which would itself make the new declaration duplicate. Assignment to
or reading an unknown name reports `E_UNDECLARED`. Assignment must preserve the
inferred declared type (`E_TYPE`). Conditions must be `Bool`; `return` and
`print` require `Int` (`E_TYPE`).

“Function-scoped” means a name is unique across the function, including nested
blocks. Visibility is also path-sensitive: after an `if`, a name is usable only
if it is declared on every branch that can continue. Declarations made only in
a `while` body are not visible after the loop because the body may run zero
times. A branch that returns does not participate in the continuation merge.

Every reachable path through `run()` must return an `Int`; otherwise report
`E_MISSING_RETURN`. A `return` makes the rest of its block unreachable and any
following statement in that block produces `E_UNREACHABLE`. An `if` terminates
only when both branches terminate. A `while` is conservatively considered able
to fall through, even when its condition is `true`.

At most 255 locals may be declared (`E_LIMIT`). Expression nesting, statement
nesting, and token count must each have documented finite limits and report
`E_LIMIT`, never `StackOverflowError` or unbounded resource use. The reference
budgets are 256 nesting levels and 100,000 tokens.

## 5. Runtime and JVM artifact contract

On success, bytes must begin with class-file magic `CA FE BA BE`, define exactly
the requested public final class, and be loadable on Java 17. It must expose:

```text
public static int run()
```

Calling `run()` executes the program. `print e;` writes the decimal integer and
one platform line separator to the current `System.out`. Arithmetic uses normal
JVM signed 32-bit behavior. Division or remainder by zero throws
`ArithmeticException`. Comparisons and boolean values are represented canonically
as `0` or `1`, though this representation is not observable in typed source.
`&&` and `||` must short-circuit.

Generated class files target major version 49 so branch targets do not require a
`StackMapTable`. All control-flow joins must nevertheless have compatible stack
heights and types. The `run` operand stack must remain within its declared
`max_stack`, branches must fit signed 16-bit offsets, and method code must remain
within 65,535 bytes. Exceeding a backend limit reports `E_LIMIT`.

For identical source and class name, successful output bytes must be identical.
Do not embed timestamps, paths, hash iteration order, or host-specific metadata.

## 6. Acceptance

Public tests are a smoke test, not the whole specification. Independent tests
will check malformed source, all operators, precedence, locations, scope, type
errors, return analysis, short-circuit behavior, loops, JVM verification,
determinism, defensive copies, and resource limits. No validator label may be
self-awarded by the implementation.
