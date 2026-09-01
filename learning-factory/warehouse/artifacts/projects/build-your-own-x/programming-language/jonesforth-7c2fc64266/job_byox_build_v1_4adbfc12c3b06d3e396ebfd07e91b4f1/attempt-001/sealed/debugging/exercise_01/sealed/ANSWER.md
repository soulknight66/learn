# Answer

In GNU as Intel syntax, the bare symbolic operand in mov edx, message_length is parsed as an absolute
memory operand. The generated instruction attempts to load a 32-bit value from address 16 instead
of loading the constant 16. That low-address access normally faults before write.

Use an explicit immediate form:

    mov edx, OFFSET FLAT:message_length

A regression test must require all three observations: exit status 3, empty standard output, and
standard error exactly stack underflow plus newline. Merely checking for a nonzero exit would allow
the crash to masquerade as correct error handling.

