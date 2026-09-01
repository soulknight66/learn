# Debugging exercise 01: the diagnostic that crashes

A GNU as Intel-syntax program reaches its stack-underflow label, but instead of writing the expected
message it terminates abnormally. Disassembly shows a load from a very low virtual address before
the write syscall.

Inspect buggy_length.S. Explain why an assembler constant naming the message length did not become
an immediate operand, propose the smallest correction, and state how a test should distinguish the
bug from a normal status-3 language failure. Do not run the fixture where crash dumps are unsafe.

