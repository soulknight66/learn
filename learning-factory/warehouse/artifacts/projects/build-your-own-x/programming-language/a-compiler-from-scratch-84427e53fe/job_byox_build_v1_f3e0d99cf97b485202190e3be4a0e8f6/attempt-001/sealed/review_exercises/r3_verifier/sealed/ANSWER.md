# R3 answer

Before output, validate the entire instruction array: known opcode, exact arity, constant domain, local bounds, jump bounds, and at least one `HALT`. A stronger data-flow verifier propagates stack height and abstract types through every reachable edge and requires compatible merge states. Scanning all instruction shapes also rejects a malformed unreachable instruction rather than letting control flow hide it.
