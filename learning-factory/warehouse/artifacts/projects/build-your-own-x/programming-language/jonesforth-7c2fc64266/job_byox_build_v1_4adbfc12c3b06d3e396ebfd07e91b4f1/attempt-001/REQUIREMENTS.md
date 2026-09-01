# Observable requirements

The words MUST, MUST NOT, and SHOULD describe the grading contract. Internal bytecode values,
register assignments, and label names are intentionally unspecified.

## Build and process interface

R1. Running make -C starter clean all MUST create starter/stackvm as an x86-64 Linux ELF executable.
It MUST enter through its own _start symbol and use Linux system calls rather than libc.

R2. stackvm MUST read the complete source program from standard input through end-of-file. It MUST
write language results only to standard output and diagnostics only to standard error. Empty input
MUST succeed silently.

R3. At most 4095 input bytes are accepted. Any input of 4096 bytes or more MUST fail before
tokenization with status 6 and exactly input too large followed by a newline on standard error.
Accepted input may arrive through several short reads.

## Source language

R4. Every byte from 0x00 through 0x20 is a separator. One or more other bytes form a token. There
are no comments, quoted strings, or user-defined words. Built-in words are lowercase and
case-sensitive.

R5. A decimal literal has grammar -?[0-9]+ and represents a signed 64-bit two's-complement value.
Both -9223372036854775808 and 9223372036854775807 MUST be accepted. A malformed or out-of-range
token is a compile error.

R6. The following tokens MUST have these effects. The rightmost item is the top of the data stack.

    token     before       after / observable effect
    literal  ( -- n )      push n
    +        ( a b -- s )  checked signed a + b
    -        ( a b -- d )  checked signed a - b
    *        ( a b -- p )  checked signed a * b
    /        ( a b -- q )  signed a / b, truncated toward zero
    dup      ( a -- a a )
    drop     ( a -- )
    swap     ( a b -- b a )
    over     ( a b -- a b a )
    =        ( a b -- f )  push 1 when equal, otherwise 0
    .        ( a -- )      print a in canonical decimal followed by newline

Division by zero has its own error. The otherwise unrepresentable division
-9223372036854775808 / -1 is arithmetic overflow. No operation may silently wrap.

R7. The data stack MUST hold 256 signed 64-bit cells. An operation first checks all required input
cells and then any required output capacity. A 257th live cell is a stack overflow. Ending with
unused values on the stack is successful.

## Compilation and execution

R8. The whole token stream MUST be validated and compiled to a bounded internal representation
before its first instruction executes. Consequently, 1 . unknown MUST produce no standard output:
the later compile error prevents all execution. The bytecode representation itself is private and
need not match any reference layout.

R9. After successful compilation, instructions execute in source order. A runtime error stops
immediately. Output already produced by earlier runtime instructions is not rolled back.

## Failures

R10. A successful run exits 0 with empty standard error. A failure emits exactly one listed line and
uses the corresponding nonzero status:

    status  standard error
       1    read error
       2    compile error
       3    stack underflow
       4    stack overflow
       5    division by zero
       6    input too large
       7    arithmetic overflow
       8    program too large
       9    internal bytecode error

Each phrase above is followed by one newline. Status 8 is a defensive bound check; an implementation
with enough code storage for every accepted 4095-byte source SHOULD make it unreachable from source
input. Status 9 protects the VM from an impossible opcode and is not a source-language feature.

## Quality constraints

R11. Input, bytecode, stacks, and formatting buffers MUST be statically bounded. Executable code
MUST NOT be writable. The implementation MUST NOT invoke a shell, open files, or access the network.

R12. The public suite is a behavioral sample. Implementations are also expected to handle short
reads, separator bytes, numeric boundaries, arithmetic overflow, compile-before-execute atomicity,
and all stack capacity transitions under independent tests.

