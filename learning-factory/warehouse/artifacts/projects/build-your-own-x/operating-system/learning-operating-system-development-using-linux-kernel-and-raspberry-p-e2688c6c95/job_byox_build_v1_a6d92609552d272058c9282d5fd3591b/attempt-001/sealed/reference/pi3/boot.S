.section .text.boot
.global _start
.type _start, %function

_start:
    mrs x0, mpidr_el1
    and x0, x0, #3
    cbnz x0, .Lpark
    ldr x0, =__stack_top
    mov sp, x0
    bl pi_main

.Lpark:
    wfe
    b .Lpark

.size _start, . - _start
