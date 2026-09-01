# Exercise 01 answer

JVM branch offsets are signed 16-bit values relative to the address of the
branch opcode, not the address immediately after its operands. The subtraction
must be `targetPosition - opcodePosition`, followed by an explicit signed-range
check before writing two bytes.

Test a forward conditional whose target begins with a distinctive instruction
and a backward loop branch. Place enough variable-width instructions between
them to prevent an accidental alignment from hiding the defect. Also test exact
accepted/rejected spans around `Short.MIN_VALUE` and `Short.MAX_VALUE` without
narrowing before the comparison.

