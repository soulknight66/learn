# Concepts behind the challenge

## Syntax is data

An s-expression reader has two jobs that are easy to conflate: lexical analysis finds boundaries and
source positions, while parsing discovers nesting. Keeping `Token` separate from the resulting value
tree makes malformed input diagnosable without contaminating runtime values with parser machinery.
Reader shorthand is a syntax transformation: quote punctuation becomes an ordinary list before the
evaluator sees it.

## Names require places, not substitutions

Lexical scope is naturally represented as environments connected by parent links. A closure retains
the environment in which it was created, not the one from which it is later called. Mutation makes
the distinction between “find a binding” and “create a binding” observable, especially when the same
name exists in several scopes.

## Special forms control evaluation

A regular function receives evaluated arguments, so it cannot implement short-circuiting or binding
syntax. Forms such as `if`, `let`, and `fn` must decide which children to evaluate and in which
environment. Writing those decisions explicitly turns evaluation order into a testable language-design
choice.

## A compiler changes representation, not meaning

The compiler converts a value tree into a linear instruction sequence. Forward branches require
backpatching once their destinations are known. The VM then makes intermediate state explicit as an
instruction pointer and operand stack. Differential tests against the evaluator are powerful because
the two engines reach the same result through substantially different mechanisms.

## Limits are part of semantics

Recursive interpreters otherwise inherit accidental limits and errors from their host. A language-level
step counter and call-depth counter provide deterministic failure modes. Place checks at semantic
boundaries, document what consumes budget, and test the exact boundary rather than relying on wall
clock time.

## Errors are an API

A stable machine-readable error code lets callers react without matching prose. Host exceptions are
implementation details; translate them at the boundary where enough language context remains to say
what went wrong.
