# Sealed design rationale

## Representation

Pebble uses host `None`, exact `bool`, exact `int`, `str`, and `list` for the corresponding immutable or
copy-on-construction data values. `Symbol` is a frozen tagged record, preventing string literals from
participating in lookup. `Builtin` and `UserFunction` are identity-bearing records with equality disabled;
language equality explicitly rejects callables.

Syntax lists and runtime lists share a representation because the language has no list mutation. Quote can
therefore return its input safely within language semantics. Host callers can still mutate returned lists,
which is one reason the reference is educational rather than production hardened.

## Reader ownership

`tokenize` owns character classification, string decoding, and one-based token starts. `_TokenReader`
owns nesting and quote expansion. End-of-input structural errors point to the construct that opened, while
unknown escapes point to the backslash. This division avoids reconstructing source positions during
recursive parsing.

## Environments and definitions

An `Environment` is a dictionary and parent link. Function construction captures the current object, so a
returned closure retains its defining frame. Calls parent a fresh parameter frame to that captured object,
never to the caller. `def` deliberately writes to the interpreter's global frame even if evaluated in a
function; the expression itself is evaluated in the current scope.

`let` uses one child frame and evaluates bindings sequentially in it. Repeated binding names are permitted
and replace the earlier value because the language contract forbids only duplicate function parameters.

## Evaluator control flow

The evaluator is a loop over `(current, scope)`. Literal and ordinary call operands use nested evaluation,
but tail positions replace that pair and continue:

- the chosen `if` branch;
- the final `do` expression;
- the final `let` body expression; and
- the final user-function body expression.

Earlier body expressions are evaluated for effects before replacement. A user call evaluates its operator
and operands first, builds a closure-parented frame, evaluates nonfinal body forms, and loops on the final
form. Consequently mutually tail-recursive functions also retain constant Python stack usage.

## Built-in boundary

`Builtin.invoke` owns uniform arity enforcement. Each numeric built-in checks `type(value) is int`, rather
than `isinstance`, to exclude booleans. Division computes a sign and divides absolute integers, avoiding
float conversion and implementing truncation toward zero for arbitrary-size operands. Collections return
new list shells. The configured output callback is the only evaluator-side effect and its failures become
`EvalError`.

## Optional compiler

The compiler targets a small stack machine. It supports data, global loads, quote, conditional jumps,
sequencing, and calls; `def`, `let`, and `fn` are rejected. This explicit boundary avoids pretending that a
global-only VM implements closure semantics. Conditional jumps pop their conditions, every expression
leaves one result, `POP` discards nonfinal `do` values, and `RETURN` requires exactly one stack value.

The VM reuses the interpreter's built-in objects, which makes differential output and error behavior easy
to compare. It validates indices, jump targets, arities, underflow, instruction names, and final stack
shape, but it is not a hostile-bytecode sandbox.
