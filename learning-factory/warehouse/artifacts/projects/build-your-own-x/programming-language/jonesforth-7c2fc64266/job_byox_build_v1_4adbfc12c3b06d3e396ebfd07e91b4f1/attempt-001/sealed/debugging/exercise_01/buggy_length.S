.intel_syntax noprefix
.global _start

.section .text
_start:
    lea rsi, [rip + message]
    mov edx, message_length
    mov eax, 1
    mov edi, 2
    syscall
    mov eax, 60
    mov edi, 3
    syscall

.section .rodata
message:
    .ascii "stack underflow\n"
.equ message_length, . - message

.section .note.GNU-stack,"",@progbits

