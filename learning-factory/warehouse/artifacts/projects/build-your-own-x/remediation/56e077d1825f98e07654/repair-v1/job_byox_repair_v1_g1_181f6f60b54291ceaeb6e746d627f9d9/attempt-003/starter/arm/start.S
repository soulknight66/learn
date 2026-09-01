.syntax unified
.cpu cortex-a15
.arm

.section .text.boot, "ax"
.global _start
.type _start, %function
_start:
    /* TODO: select a privileged mode, initialize sp, clear .bss, call arm_kernel_main. */
1:
    wfi
    b 1b
.size _start, . - _start
