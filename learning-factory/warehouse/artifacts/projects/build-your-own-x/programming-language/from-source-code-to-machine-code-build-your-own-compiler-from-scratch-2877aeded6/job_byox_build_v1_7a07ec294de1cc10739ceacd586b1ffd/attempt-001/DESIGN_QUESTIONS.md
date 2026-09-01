# Design questions

Record your answers before implementation, then revisit them after tests expose tradeoffs.

1. Which lexer state owns CRLF normalization, and what position should EOF have?
2. How will parser functions avoid consuming the first token of the next construct?
3. Will AST nodes retain full tokens, only source spans, or no locations? Why?
4. At exactly what point does a `let` name enter its scope?
5. Will slot allocation be monotonic or lifetime-aware? Which invariant makes it safe?
6. What does the emitter store when it cannot yet know a forward jump destination?
7. How will you distinguish a jump to an opcode from a jump into an operand?
8. What graph algorithm will prove stack depth at all reachable instruction boundaries?
9. How will you implement truncating signed division without floating point?
10. Which failures must occur before any observable output, and how will the code enforce that order?
11. How can `compile SOURCE OUTPUT` avoid corrupting a pre-existing output on failure?
12. Which limits belong in this educational VM, and which remain productionization work?
