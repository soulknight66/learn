BITS 32

SECTION .multiboot
ALIGN 4
    dd 0x1BADB002
    dd 0x00000003
    dd -(0x1BADB002 + 0x00000003)

SECTION .bss
ALIGN 16
stack_bottom:
    resb 16384
stack_top:

SECTION .text
GLOBAL _start
EXTERN kernel_main
_start:
    mov esp, stack_top
    push ebx
    push eax
    call kernel_main
.halt:
    cli
    hlt
    jmp .halt

SECTION .note.GNU-stack noalloc noexec nowrite progbits
