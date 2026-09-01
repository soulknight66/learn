# Sealed design answers

## Architecture

The executable has three phases: accumulate bounded input, compile tokens, and execute bytecode. No
language instruction runs until a halt opcode has been appended after successful compilation.

During input, r12 is the byte count. During compilation, r12 and r13 are the source cursor and end,
r15 is the code cursor, rbx/r14 describe the current token, and r9 records a negative literal.
During execution, r12 is the instruction pointer, r14 is the stack base, and r15 is stack depth.
Formatting deliberately avoids those three VM-state registers.

## Token and literal decisions

Bytes at or below 0x20 are skipped in place. A token is only a start pointer plus a length. The
one-byte minus token is recognized as an operator before numeric parsing; a longer leading-minus
token enters the numeric parser.

Numeric parsing accumulates positive inputs with add and negative inputs with subtract. Each
multiply and update checks the overflow flag. Negative accumulation admits -9223372036854775808
without constructing its impossible positive counterpart.

## Private bytecode

One-byte opcodes represent built-ins. A literal is a push opcode followed by an unaligned 64-bit
immediate. Unaligned loads are defined on x86-64. A halt byte terminates execution. The VM rejects
every unknown opcode even though the compiler cannot emit one.

The 32,768-byte code region is enough for accepted input. The most expansive source form is a
one-byte literal separated by one byte, producing about 9/2 code bytes per input byte; 4095 bytes
therefore need fewer than 18,432 code bytes plus halt. Every emission is still bounds-checked.

## Stack and arithmetic

Depth is a cell count from 0 through 256. Operations check all input depth before output capacity
and mutate only after checks. Binary arithmetic replaces the lower operand and decrements depth.
Processor overflow flags implement checked add, subtract, and multiply. Division separately rejects
zero and the signed minimum divided by -1 before idiv.

Equality stores 1 or 0. Decimal formatting keeps every nonzero magnitude negative, so both ordinary
negative values and the signed minimum use the same idiv loop. A leading minus is added only for an
originally negative input.

## Error timing

Compile failures occur before VM entry and therefore before output. Runtime failures stop at the
first bad instruction, leaving previously written output visible. Each normal error label chooses
one fixed message and exit status before entering the common failure path.

