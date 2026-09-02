.syntax unified
.cpu arm926ej-s
.arm

.section .text.context, "ax", %progbits
.global lf_arch_context_switch
.type lf_arch_context_switch, %function
lf_arch_context_switch:
    stmia r0, {r4-r11, sp, lr}
    ldmia r1, {r4-r11, sp, lr}
    bx lr
.size lf_arch_context_switch, . - lf_arch_context_switch

.section .note.GNU-stack, "", %progbits
