# Design questions

Record concise answers before or alongside your implementation.

1. What invariant does each parser function establish about the current lookahead token on success?
2. Why does emitting an arithmetic instruction after parsing its right operand naturally produce stack-machine evaluation order?
3. At what moment should a new `let` binding enter the symbol table? How does your choice affect `let x = x + 1;`?
4. Which malformed bytecode conditions can the compiler never produce, and why should the VM check them anyway?
5. Give boundary examples for addition, subtraction, multiplication, negation, and division. How will you check them without first executing an overflowing C expression?
6. What user-visible behavior changes if variables become mutable? Identify grammar, opcode, and name-resolution changes separately.
7. Fixed arrays make exhaustion deterministic. What ownership and failure rules would be necessary to replace them with dynamic storage?
8. Should runtime errors preserve output from earlier `print` instructions or buffer output transactionally? Defend one contract.
9. How would source spans, rather than single line numbers, improve diagnostics? What memory cost would they add to bytecode?
10. Which parts of this compiler would need redesign to add lexical block scope or forward references?
