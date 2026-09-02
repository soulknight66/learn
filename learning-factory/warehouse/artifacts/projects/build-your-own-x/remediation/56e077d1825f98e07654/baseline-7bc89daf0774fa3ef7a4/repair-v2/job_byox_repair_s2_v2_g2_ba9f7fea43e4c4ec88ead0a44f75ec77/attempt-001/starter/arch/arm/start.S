.syntax unified
.cpu arm926ej-s
.arm

.section .text.boot, "ax", %progbits
.global _start
.type _start, %function
.extern kernel_main
.extern __bss_start
.extern __bss_end
.extern __stack_top

_start:
    mrs r0, cpsr
    orr r0, r0, #0xc0
    msr cpsr_c, r0
    ldr sp, =__stack_top

    mov r0, #0
    ldr r1, =__bss_start
    ldr r2, =__bss_end
1:
    cmp r1, r2
    strlo r0, [r1], #4
    blo 1b

    bl kernel_main
2:
    b 2b
.size _start, . - _start

.section .note.GNU-stack, "", %progbits
