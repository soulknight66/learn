# Design questions

Answer these before or while implementing. They are prompts, not requirements beyond the contract.

1. Which registers hold the input cursor, token bounds, code cursor, instruction pointer, stack
   depth, and stack base? Which of them can a syscall or helper overwrite?
2. How will the tokenizer distinguish a one-byte minus operator from the beginning of a negative
   literal?
3. Can the numeric parser accept the most-negative signed integer without first constructing its
   unrepresentable positive magnitude?
4. What bound proves that the code buffer can represent every valid tokenization of 4095 input
   bytes? If you use a smaller buffer, where is the checked failure?
5. At exactly what point does each stack operation check underflow and overflow? Could a failing
   operation partially mutate the stack?
6. How will checked addition, subtraction, multiplication, and the special signed-division case map
   processor flags to language errors?
7. Why does compiling the entire program before VM entry guarantee that a later unknown word cannot
   leave earlier output?
8. How does decimal output handle zero and -9223372036854775808 without negating the latter into an
   invalid signed value?
9. What happens if read returns fewer bytes than requested even though EOF has not arrived?
10. Which behavior belongs to the language contract, and which details should remain private so the
    bytecode can evolve?

