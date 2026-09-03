# Concepts and implementation notes

## Tokens are evidence, not just categories

A token should retain the exact source slice and a decoded literal separately. That distinction
lets diagnostics quote what the learner typed while runtime code receives an already validated
value. Track the position as characters are consumed; retrofitting line information later tends to
break on comments, escapes, and end-of-file errors.

## Recursive descent mirrors precedence

Give each precedence level one parsing function. A function parses its tighter-precedence operand,
then folds repeated operators at its own level. Assignment is the exception: parsing its right side
recursively makes it right-associative. Validate the left side before constructing an assignment
node.

## Environments model names independently of values

A stack of scopes is sufficient for this language. Definition touches only the current scope;
lookup and assignment search outward. Keep “missing binding” distinct from “binding whose value is
nil,” because JavaScript map lookup can otherwise blur those cases.

## An interpreter makes semantics executable

The tree evaluator is the simplest executable definition of the language. Centralize truthiness,
display formatting, numeric checks, and binary operations so that edge cases do not drift across AST
node handlers. Evaluate operands exactly once and in left-to-right order.

## A compiler resolves structure into addresses

AST control flow has nested shape; bytecode control flow uses numeric program counters. A common
technique is to emit a jump with a temporary operand, compile the destination region, then patch the
operand to the current code length. Be explicit about whether a conditional jump consumes or merely
observes its condition.

## A VM is a state-transition system

At any point the VM state is `(program counter, operand stack, scope stack, output)`. Define each
opcode as a checked transition. Validate operands, stack depth, and scope balance before using them.
This turns corrupted bytecode into a controlled diagnostic instead of accidental JavaScript
behavior.

## Differential testing catches semantic drift

Once both backends exist, run the same source through each and compare returned values, output, and
error codes. Small generated expression trees are especially good at exposing precedence, operand
order, and stack-effect bugs. Differential agreement is useful evidence, but two implementations
can share the same mistake, so keep direct examples too.
