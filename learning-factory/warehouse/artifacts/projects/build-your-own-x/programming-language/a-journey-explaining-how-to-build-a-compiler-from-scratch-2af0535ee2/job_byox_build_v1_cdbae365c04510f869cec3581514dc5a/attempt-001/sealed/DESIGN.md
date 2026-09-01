# Reference design answers

## Front end

Tokens are borrowed slices into the source and carry type, byte pointer, byte length, one-based line
and column, plus a decoded integer when applicable. The source remains alive for the entire compile,
so token spelling requires no allocation. Scanning advances one byte at a time; exact token length is
part of every keyword comparison.

The expression ladder is logical-or, logical-and, equality, comparison, term, factor, unary, and
primary. Binary levels loop, which makes them left-associative. Unary recurses before emitting its
operator. Two-character operators inspect and conditionally consume the second byte. Lone ampersand
and pipe tokens become lexical errors at their first byte.

An initializer compiles before its new symbol is installed. Consequently a nested declaration can
read an outer binding with the same name, while a first declaration cannot read itself. Symbols are
borrowed name slices plus scope depth and stable slot. Reverse lookup chooses the nearest declaration.
Leaving a block drops all entries at that depth but does not recycle slots; this simplifies immutable
bytecode and makes the symbol ceiling apply to total declarations.

## Code generation

The reference instruction is an opcode, a size_t operand, and source coordinates. This is an
instruction IR rather than a compact serialized encoding. A constant or load pushes one value; store,
print, and conditional jump consume one; binary instructions consume two and produce one. Unary
instructions preserve depth. Both compiler and VM enforce their view of these effects.

Jumps hold absolute instruction indexes. Forward branches are emitted with a zero placeholder and
patched only through a helper that checks the instruction and target indexes. Backward loop targets
are already known. A false conditional jump always consumes its condition.

Logical AND emits a false jump for each operand, then pushes one on the all-true path or zero at the
shared false label. Logical OR jumps from a false left operand into right evaluation, while a true
left operand pushes one and skips the right side. This both short-circuits and normalizes results.

## VM and failures

Compilation allocates a private program and publishes it only after EOF and HALT emission succeed.
Every failure frees code, constants, symbols, and the program shell. The program contains no stream or
VM state. Each execution allocates fresh locals and stack, so repeated runs are independent.

Instruction targets, pool indexes, local indexes, stack effects, and HALT depth are checked at
runtime. One budget unit is charged before dispatching every instruction, including HALT and jumps.
The limit test happens before increment, so a budget of N permits exactly N dispatches.

Addition and subtraction use direction-specific boundary comparisons. Multiplication divides the
appropriate signed bound by one operand before multiplying. Negation rejects INT64_MIN. Division and
remainder reject zero and the INT64_MIN/-1 pair before evaluating the C operator.

Lexical and semantic diagnostics use the offending token's starting location. Operators carry their
own location into bytecode so runtime arithmetic faults point to the operation. Newline alone advances
the line; carriage return is ordinary whitespace, making CRLF advance exactly one line.

Compilation limits code, constants, total slots, and abstract expression stack depth. Execution
rechecks code, constants, and slots against caller limits, then enforces stack and step limits while
running. Limit exhaustion is distinct from source errors and system allocation failures.
