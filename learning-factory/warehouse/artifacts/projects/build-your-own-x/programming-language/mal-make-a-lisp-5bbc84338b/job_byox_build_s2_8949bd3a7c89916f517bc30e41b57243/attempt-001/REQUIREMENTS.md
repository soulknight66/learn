# Pebble Lisp requirements

This document is normative. “Must” marks required behavior; examples are observable contracts.

## 1. Source and reader

Input is Unicode text. Spaces, tabs, carriage returns, newlines, and commas separate tokens. A semicolon
outside a string starts a comment through the next newline. The punctuation tokens are `(`, `)`, and
apostrophe. A token carries a one-based start line and column for diagnostics.

The reader must recognize:

- arbitrary-precision base-10 integers matching `[+-]?[0-9]+`;
- double-quoted strings with only `\\`, `\"`, `\n`, `\r`, and `\t` escapes;
- the exact literals `true`, `false`, and `nil`;
- every other nonempty atom as a case-sensitive symbol; and
- parenthesized lists, including the empty list.

Raw newlines, unknown escapes, and end of input inside strings are reader errors. An unmatched `)`, an
unclosed list, empty input to `read_one`, and trailing forms passed to `read_one` are reader errors.
`read_all` instead returns zero or more forms. Apostrophe is reader sugar: `'x` produces the same syntax
tree as `(quote x)`; a missing following form is an error.

## 2. Values and printing

Runtime values are integers, strings, booleans, `nil`, symbols, lists, built-ins, and user functions.
Integers and booleans must remain distinct even though Python makes `bool` an `int` subclass.

The canonical printer emits `true`, `false`, and `nil`; decimal integers; symbols unchanged; lists in
parentheses separated by one space; and strings with the same five escapes as the reader. Built-ins print
as `<builtin:name>` and user functions as `<fn>`. This representation must be deterministic.

## 3. Evaluation

Literal values and the empty list evaluate to themselves. A symbol resolves through the current lexical
environment, then its parents; an absent name raises `NameResolutionError`. A nonempty list is either a
special form or a call. Evaluation is left-to-right. Only `false` and `nil` are falsey.

Special forms are reserved only in operator position:

- `(quote form)` takes exactly one unevaluated argument.
- `(if condition then [else])` takes two or three arguments and returns `nil` when a false condition has
  no else branch. Only the selected branch is evaluated.
- `(do form...)` evaluates left-to-right and returns the final value, or `nil` with no forms.
- `(def name expression)` requires a symbol, evaluates once, and binds in the interpreter's global
  environment. It returns the value.
- `(let ((name expression) ...) body...)` creates one child environment. Bindings are evaluated in order
  in that child, so later initializers see earlier bindings. At least one body form is required.
- `(fn (parameter...) body...)` captures the current environment. Parameters must be distinct symbols,
  and at least one body form is required. Calls require exactly the declared arity.

The final expression of `if`, `do`, `let`, and a user-function body is a tail position. A correct
implementation must evaluate at least 5,000 tail-recursive calls without changing Python's recursion
limit and without raising `RecursionError`.

## 4. Built-ins

The initial global environment must contain the following names:

| Name | Arity | Contract |
| --- | ---: | --- |
| `+` | 0+ | Integer sum; identity `0`. |
| `*` | 0+ | Integer product; identity `1`. |
| `-` | 1+ | Unary negation, otherwise left fold subtraction. |
| `/` | 2 | Integer quotient truncated toward zero; division by zero is an `EvalError`. |
| `=` | 2 | Structural equality for data values; callable values compare unequal. |
| `<`, `<=`, `>`, `>=` | 2 | Integer comparisons. |
| `list` | 0+ | A new list containing its arguments. |
| `first` | 1 | First list element; `nil` for an empty list or `nil`. |
| `rest` | 1 | New list without the first element; empty list for empty list or `nil`. |
| `cons` | 2 | A new list with the first argument prepended to a list second argument. |
| `empty?` | 1 | True only for an empty list or `nil`. |
| `count` | 1 | Length of a list or string; zero for `nil`. |
| `not` | 1 | True exactly when its argument is falsey. |
| `pr-str` | 1 | Canonical printed representation as a host string value. |
| `str` | 0+ | Concatenate strings unchanged and other values canonically printed. |
| `print` | 1 | Send canonical text to the configured output sink and return `nil`. |

Wrong arity raises `ArityError`. Wrong operand type and attempts to call data raise `EvalError`. No raw
host exception may cross the interpreter API for a well-formed API call.

## 5. Public API and CLI

The scaffold's public classes, functions, and exceptions must remain importable. `Interpreter.eval_source`
evaluates all forms in one persistent global environment and returns the final value, or `nil` for empty
source.

`python3 -m pebble.cli -e SOURCE` prints the final canonical value plus a newline. A file argument reads
UTF-8 and evaluates it; only explicit Pebble `print` calls produce stdout in file mode. With neither, the
CLI runs a prompt, retains globals across lines, skips blank input, and prints each result. Language and
I/O failures produce `error: <message>` on stderr and status 2, without a traceback. Invalid CLI syntax
uses the argument parser's normal nonzero behavior.

## 6. Safety and implementation boundaries

Use the standard library only. Do not implement semantics through Python `eval`, `exec`, or `compile`.
Do not invoke a shell. Treat source as data, and bound only host I/O at the CLI boundary.

## 7. Optional compiler extension

As a stretch goal, compile the pure expression subset (literals, symbol loads, `quote`, `if`, `do`, and
built-in calls) to explicit bytecode. Reject unsupported forms deterministically rather than silently
changing semantics. Differential tests should compare the evaluator and VM for supported programs.
