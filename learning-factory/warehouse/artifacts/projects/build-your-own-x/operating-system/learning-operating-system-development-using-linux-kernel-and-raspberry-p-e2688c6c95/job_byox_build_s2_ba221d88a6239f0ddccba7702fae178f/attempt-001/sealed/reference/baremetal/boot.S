.section .text.boot, "ax"
.global _start
.type _start, %function

_start:
    mrs x0, mpidr_el1
    and x0, x0, #0xff
    cbnz x0, .Lpark

    ldr x0, =__bss_start
    ldr x1, =__bss_end
.Lclear_bss:
    cmp x0, x1
    b.hs .Lbss_done
    str xzr, [x0], #8
    b .Lclear_bss
.Lbss_done:
    ldr x0, =__stack_top
    mov sp, x0
    bl kernel_main

.Lpark:
    wfe
    b .Lpark

.size _start, . - _start
