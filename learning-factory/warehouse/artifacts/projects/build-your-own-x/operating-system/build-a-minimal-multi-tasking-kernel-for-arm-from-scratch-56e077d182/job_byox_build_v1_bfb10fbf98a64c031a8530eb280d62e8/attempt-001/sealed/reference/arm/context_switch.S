.syntax unified
.cpu cortex-a15
.arm

.text
.align 2
.global arm_context_switch
.type arm_context_switch, %function
/* r0 = address of old stack pointer; r1 = new stack pointer. */
arm_context_switch:
    push {r4-r11, lr}
    str sp, [r0]
    mov sp, r1
    pop {r4-r11, lr}
    bx lr
.size arm_context_switch, . - arm_context_switch
