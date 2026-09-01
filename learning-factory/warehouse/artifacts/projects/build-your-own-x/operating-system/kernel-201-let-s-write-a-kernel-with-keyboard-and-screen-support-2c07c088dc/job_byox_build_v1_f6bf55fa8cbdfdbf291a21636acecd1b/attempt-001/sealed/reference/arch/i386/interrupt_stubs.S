.section .text
.code32

.global idt_load
.type idt_load, @function
idt_load:
    movl 4(%esp), %eax
    lidt (%eax)
    ret
.size idt_load, . - idt_load

.global keyboard_isr_stub
.type keyboard_isr_stub, @function
.extern keyboard_isr_c
keyboard_isr_stub:
    pusha
    cld
    call keyboard_isr_c
    popa
    iret
.size keyboard_isr_stub, . - keyboard_isr_stub

.section .note.GNU-stack, "", @progbits
