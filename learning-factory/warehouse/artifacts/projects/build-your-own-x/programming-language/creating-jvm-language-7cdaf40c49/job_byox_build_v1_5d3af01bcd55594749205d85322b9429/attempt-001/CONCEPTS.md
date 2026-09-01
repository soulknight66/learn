# Concepts to master

## A pipeline with explicit boundaries

A language implementation is easier to reason about when text, syntax, meaning,
and machine representation are separate stages. Tokens retain source positions;
the parser builds structure rather than executing; semantic analysis attaches
types and local slots; the backend consumes only validated structure. Each stage
should turn expected user mistakes into data, not crashes.

## Precedence and associativity

The grammar is layered from low precedence (`||`) to high precedence (unary).
Each binary layer parses a left operand and folds repeated operator/right pairs,
giving left associativity. Unary recursion gives right association. Parentheses
restart expression parsing at the lowest layer.

## Static types as backend invariants

Sprig has only two source types, but enforcing them before code generation is
valuable. Once analysis succeeds, the emitter can assume an arithmetic node has
integer operands and a branch condition is a JVM integer boolean. That reduces
verifier failures to compiler bugs rather than user errors.

## The operand stack and local slots

JVM integer instructions consume and produce values on an operand stack. Local
variables live in numbered slots. Compiling an expression should have a simple
stack contract—usually “leave exactly one integer value”—so statement emitters
can compose it. Track peak depth rather than guessing `max_stack`.

## Structured control flow becomes jumps

An `if` needs conditional and end labels; a `while` needs header and exit labels.
Forward branch offsets cannot be known until targets are marked, so an emitter
records fixups and patches them later. Boolean comparisons generally branch to
small sequences that materialize `0` or `1`.

## Short-circuiting is observable

Logical operators are control flow, not simply integer arithmetic. The right
operand may divide by zero or run expensive code in richer languages. Emit a
branch after the left operand so the right side is skipped when its value cannot
affect the result.

## Class-file minimalism

A tiny class needs a magic/version header, a constant pool, access flags, class
identity, and a method with a `Code` attribute. The constant pool is indexed and
uses tagged entries. Multi-byte integers are big-endian. JVM branch offsets are
relative to the opcode address, not to the following instruction.

## Diagnostics and limits are language design

Locations, stable error codes, deterministic ordering, and explicit budgets are
part of the compiler’s public behavior. Resource limits prevent malicious input
from turning recursive descent or bytecode buffers into denial-of-service tools.

