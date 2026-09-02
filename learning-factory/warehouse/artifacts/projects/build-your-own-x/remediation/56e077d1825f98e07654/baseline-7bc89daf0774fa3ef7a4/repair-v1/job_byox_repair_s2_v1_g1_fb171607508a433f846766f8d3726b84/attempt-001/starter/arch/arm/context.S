.syntax unified
.cpu arm926ej-s
.arm

.section .text.context, "ax", %progbits
.global lf_arch_context_switch
.type lf_arch_context_switch, %function
lf_arch_context_switch:
    /* Stage 2: save the old callee-saved context, restore the new one, and
       continue at the restored link register. */
    bx lr
.size lf_arch_context_switch, . - lf_arch_context_switch

.section .note.GNU-stack, "", %progbits
