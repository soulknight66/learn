.syntax unified
.cpu cortex-a15
.arm

.section .text.boot, "ax"
.global _start
.type _start, %function
_start:
    cpsid if
    ldr sp, =__stack_top
    ldr r0, =__bss_start
    ldr r1, =__bss_end
    mov r2, #0
1:
    cmp r0, r1
    strlo r2, [r0], #4
    blo 1b
    bl arm_kernel_main
2:
    wfi
    b 2b
.size _start, . - _start
