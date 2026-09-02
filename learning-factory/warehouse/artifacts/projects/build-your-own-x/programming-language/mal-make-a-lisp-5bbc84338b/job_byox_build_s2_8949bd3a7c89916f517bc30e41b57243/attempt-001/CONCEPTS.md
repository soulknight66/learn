# Concepts before code

## Syntax is data with locations

A tokenizer decides boundaries; a reader decides nesting. Keeping those stages separate makes errors
local: the tokenizer owns malformed strings, while the reader owns unmatched parentheses. Store each
token's start position before advancing so failures identify the user's source rather than the scanner's
eventual location.

In a Lisp, the syntax tree can reuse runtime data shapes: a list node looks like a list value and a symbol
is a small tagged value. The tag matters—host strings cannot safely stand for both string literals and
names.

## Evaluation is an ordering contract

An evaluator is not just a recursive walk. It specifies which expressions run, in what environment, and
in what order. Special forms exist precisely because ordinary call rules would eagerly evaluate every
argument. `if`, `quote`, definitions, and function creation each need different control of evaluation.

## Lexical environments outlive calls

An environment is a frame plus an optional parent. A closure retains the frame present when the function
was created, not the frame present when it is later called. This is ownership, not merely dictionary
lookup: a returned function can keep a former call's bindings alive.

## Tail position changes resource use

Recursive source need not imply recursive host calls. When the evaluator has nothing left to do after an
expression, it can replace its current `(form, environment)` pair and continue a loop. Be precise about
tail positions; evaluating an operand is not a tail position because the call still remains.

## Errors belong to the language boundary

Readers, environments, arity checks, and built-ins should translate host accidents into stable language
errors. That makes the CLI predictable and tests meaningful. Catch narrowly: a blanket exception handler
inside evaluation can hide bugs as supposed user errors.

## Interpreter versus compiler

A tree walker repeatedly inspects syntax. A bytecode compiler makes control flow and operand order
explicit once, then a virtual machine executes simpler instructions. Neither is automatically faster or
safer. A useful compiler exercise first defines a supported subset, rejects everything else, and checks
observational equivalence against the interpreter.
