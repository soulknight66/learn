.intel_syntax noprefix

/*
 * Cinder learner scaffold.
 *
 * Keep _start as the process entry point. Replace the stub with a bounded tokenizer,
 * checked stacks, a compiler, and a small threaded VM satisfying REQUIREMENTS.md.
 * This file intentionally contains no reference implementation.
 */

.equ SYS_write, 1
.equ SYS_exit, 60

.section .rodata
not_implemented:
    .ascii "error: interpreter not implemented\n"
.equ not_implemented_len, . - not_implemented

.section .text
.global _start
.type _start, @function
_start:
    mov eax, SYS_write
    mov edi, 2
    lea rsi, [rip + not_implemented]
    mov edx, not_implemented_len
    syscall

    mov eax, SYS_exit
    mov edi, 2
    syscall
.size _start, . - _start

.section .note.GNU-stack,"",@progbits
