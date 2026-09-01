# Design questions

Write down your answers before implementing each phase. Revisit them after the evaluator and VM
agree.

## Tokens and syntax

1. How will you distinguish division from the beginning of a comment without consuming too much?
2. What source position should EOF receive for empty input, trailing newlines, and CRLF input?
3. Where will parser synchronization happen after an error, if you later want to report more than
   one syntax error?
4. Would a Pratt parser or precedence-layered recursive descent be easier to extend with assignment
   expressions, and why?

## Semantics

5. Should a block introduce scope? What examples become surprising under either choice?
6. At what point should duplicate declarations and undefined assignments fail: parse time, compile
   time, or runtime?
7. Which host-language behaviors could leak into Pebble if operator checks are incomplete?
8. What unit of work should the evaluator charge against `maxSteps` so that nested empty loops are
   still bounded?

## Compiler and VM

9. State a stack-height invariant for every expression and statement form. How could a compiler
   assertion check it?
10. Which jump destination should an `if` without `else` use, and when is that address known?
11. Should bytecode validation be a separate pass or integrated into execution? Compare failure
    atomicity, complexity, and speed.
12. How will the VM distinguish an absent operand from a valid operand whose value happens to be
    `0`?
13. What data must be copied, frozen, or treated immutably so repeated executions cannot influence
    one another?

## Testing and evolution

14. Which programs isolate parser precedence from evaluator arithmetic?
15. How will you compare failures across backends without coupling tests to incidental message text?
16. What generator constraints guarantee that random programs terminate and only read initialized
    variables?
17. Choose one proposed feature—strings, local scope, logical operators, or functions—and list every
    phase and contract it would change.

