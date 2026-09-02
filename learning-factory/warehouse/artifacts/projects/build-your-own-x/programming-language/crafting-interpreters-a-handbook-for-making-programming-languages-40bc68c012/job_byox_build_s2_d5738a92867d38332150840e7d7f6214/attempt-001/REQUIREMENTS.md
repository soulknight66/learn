# Mica language requirements

## Deliverable

Complete the Java 21 sources in `starter/src/main/java/org/learningfactory/mica`. `Mica.run(source,
engine)` must tokenize and parse every invocation, then execute with either `Engine.TREE` or
`Engine.VM`. It returns an immutable list containing values produced by `print`, in source order.

Neither engine may write to standard output through this API. The CLI is the only output adapter.

## Lexical grammar

- Source is Unicode text, but identifiers use ASCII: `[A-Za-z_][A-Za-z0-9_]*`.
- Spaces, tabs, carriage returns, and newlines separate tokens.
- `//` starts a comment extending to (but not consuming) the next newline.
- Numbers are decimal: one or more digits, optionally followed by `.` and one or more digits.
- Strings use double quotes. The only escapes are `\n`, `\t`, `\"`, and `\\`.
- Keywords are `and`, `else`, `false`, `if`, `let`, `nil`, `or`, `print`, `true`, and `while`.
- Punctuation/operators are `(` `)` `{` `}` `,` `;` `+` `-` `*` `/` `!` `!=` `=` `==` `<` `<=`
  `>` `>=`.
- Every token, including EOF, reports a one-based line and column for its first character.
- Unterminated strings, invalid escapes, unexpected characters, and non-finite/out-of-range numeric
  literals are `LEX` errors located at the offending token or character.

## Syntax grammar

The notation below uses `*` for repetition and `?` for optional elements.

```text
program      -> declaration* EOF ;
declaration  -> "let" IDENTIFIER "=" expression ";" | statement ;
statement    -> "print" expression ";"
              | "if" "(" expression ")" statement ("else" statement)?
              | "while" "(" expression ")" statement
              | "{" declaration* "}"
              | expression ";" ;
expression   -> assignment ;
assignment   -> IDENTIFIER "=" assignment | logic_or ;
logic_or     -> logic_and ("or" logic_and)* ;
logic_and    -> equality ("and" equality)* ;
equality     -> comparison (("!=" | "==") comparison)* ;
comparison   -> term ((">" | ">=" | "<" | "<=") term)* ;
term         -> factor (("-" | "+") factor)* ;
factor       -> unary (("/" | "*") unary)* ;
unary        -> ("!" | "-") unary | primary ;
primary      -> NUMBER | STRING | "true" | "false" | "nil"
              | IDENTIFIER | "(" expression ")" ;
```

Assignment is right-associative. A non-variable assignment target is a `PARSE` error. Semicolons are
mandatory. Report the first deterministic syntax error; recovery is optional.

## Runtime semantics

- Values are numbers (Java `double`), strings, booleans, and `nil` (Java `null`).
- Conditions and operands of `!`, `and`, and `or` must be booleans. `and` and `or` short-circuit.
- `+` accepts two numbers or two strings. Other arithmetic operators accept two numbers.
- Comparisons accept two numbers. Division by either `0.0` or `-0.0` is an error.
- Equality is true only for two `nil` values or two same-kind equal values. Unlike numeric ordering,
  equality never raises a mixed-type error.
- A block creates a lexical scope. `let` evaluates its initializer before defining its name and may
  not redeclare a name in the same scope. Inner scopes may shadow outer names.
- Assignment updates the nearest existing binding and evaluates to the assigned value. Reading or
  assigning an undefined name is a runtime error.
- `while` re-evaluates its condition before each iteration. Both engines charge one semantic step at
  each statement dispatch (the compiler represents this with `TICK`). They must stop before semantic
  step 100,001 and raise a `LIMIT` error, preventing accidental infinite loops. The VM may also impose
  a larger raw-instruction guard on malformed bytecode that executes forever without `TICK`.
- Runtime/limit diagnostics identify the responsible source token with one-based line and column.

## Rendering and errors

`print` renders `nil`, lowercase booleans, strings without quotes, and numbers using
`Double.toString` except that an integral finite double omits `.0`. Negative zero renders `-0`.

All language failures use `MicaException` and expose `Kind` (`LEX`, `PARSE`, `RUNTIME`, or `LIMIT`),
line, column, and a stable human-readable detail. Host exceptions such as `NullPointerException` or
`IndexOutOfBoundsException` must not escape for validly tokenized input.

## Bytecode parity

The VM must execute instructions produced from the AST rather than delegating to the tree interpreter.
For every accepted program the engines produce identical output. For rejected source programs they
must agree on error kind and location. Jumps use explicit patched targets, and malformed bytecode must
be rejected as a language error rather than crashing or indefinitely occupying the host.
