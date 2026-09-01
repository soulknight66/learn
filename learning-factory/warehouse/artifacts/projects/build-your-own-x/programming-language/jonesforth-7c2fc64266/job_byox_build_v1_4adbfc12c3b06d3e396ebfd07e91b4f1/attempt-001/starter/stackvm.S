.intel_syntax noprefix
.global _start

.equ SYS_read, 0
.equ SYS_write, 1
.equ SYS_exit, 60
.equ INPUT_CAPACITY, 4096

.section .text
_start:
    xor r12d, r12d

read_more:
    xor eax, eax
    xor edi, edi
    lea rsi, [rip + input_buffer]
    add rsi, r12
    mov edx, INPUT_CAPACITY
    sub rdx, r12
    syscall
    test rax, rax
    js read_failed
    jz input_complete
    add r12, rax
    cmp r12, INPUT_CAPACITY
    je input_too_large
    jmp read_more

input_complete:
    lea rsi, [rip + input_buffer]
    lea rdx, [rsi + r12]

scan_separators:
    cmp rsi, rdx
    je exit_success
    cmp byte ptr [rsi], 0x20
    ja compile_stub
    inc rsi
    jmp scan_separators

# TODO: replace this deliberately incomplete branch with compilation and execution.
compile_stub:
    lea rsi, [rip + message_compile]
    mov edx, OFFSET FLAT:message_compile_length
    mov r8d, 2
    jmp fail

read_failed:
    lea rsi, [rip + message_read]
    mov edx, OFFSET FLAT:message_read_length
    mov r8d, 1
    jmp fail

input_too_large:
    lea rsi, [rip + message_input]
    mov edx, OFFSET FLAT:message_input_length
    mov r8d, 6

fail:
    mov eax, SYS_write
    mov edi, 2
    syscall
    mov eax, SYS_exit
    mov edi, r8d
    syscall

exit_success:
    mov eax, SYS_exit
    xor edi, edi
    syscall

.section .rodata
message_read:
    .ascii "read error\n"
.equ message_read_length, . - message_read
message_compile:
    .ascii "compile error\n"
.equ message_compile_length, . - message_compile
message_input:
    .ascii "input too large\n"
.equ message_input_length, . - message_input

.section .bss
.balign 16
input_buffer:
    .skip INPUT_CAPACITY

.section .note.GNU-stack,"",@progbits
