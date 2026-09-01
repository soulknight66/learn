# Design questions

Write down your answers before implementing. Revisit them after the public tests pass.

1. What invariants hold for the operand stack before and after every opcode?
2. How will a call recover its caller's instruction pointer and discard temporary values?
3. Where will source line numbers survive after parsing, and which runtime faults use them?
4. How will forward calls be represented before function definitions have all been seen?
5. Which checks prevent token, instruction, local, frame, and value capacities from overflowing?
6. How will you distinguish a missing input file (exit 66) from invalid source (exit 65)?
7. How will you detect each signed arithmetic overflow without first invoking undefined C
   behavior?
8. What does one execution “step” mean, and exactly when is the budget checked?
9. Which constructs need backpatching, and what makes each patch target valid?
10. How will short-circuiting avoid evaluating the right operand while still normalizing results?
11. What evidence demonstrates nested interpretation without claiming full source self-hosting?
12. Which new feature would most increase the trusted computing surface: arrays, strings,
    pointers, native calls, or dynamic allocation? Why?
