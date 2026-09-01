.intel_syntax noprefix
.global _start

.equ SYS_read, 0
.equ SYS_write, 1
.equ SYS_exit, 60

.equ INPUT_CAPACITY, 4096
.equ CODE_CAPACITY, 32768
.equ STACK_CELLS, 256

.equ OP_HALT, 0
.equ OP_PUSH, 1
.equ OP_ADD, 2
.equ OP_SUB, 3
.equ OP_MUL, 4
.equ OP_DIV, 5
.equ OP_DUP, 6
.equ OP_DROP, 7
.equ OP_SWAP, 8
.equ OP_OVER, 9
.equ OP_EQUAL, 10
.equ OP_DOT, 11

.section .text
_start:
    xor r12d, r12d

read_more:
    mov eax, SYS_read
    xor edi, edi
    lea rsi, [rip + input_buffer]
    add rsi, r12
    mov edx, INPUT_CAPACITY
    sub rdx, r12
    syscall
    test rax, rax
    js error_read
    jz input_complete
    add r12, rax
    cmp r12, INPUT_CAPACITY
    je error_input_large
    jmp read_more

input_complete:
    mov rbx, r12
    lea r12, [rip + input_buffer]
    lea r13, [r12 + rbx]
    lea r15, [rip + code_buffer]
    jmp compile_next

compile_next:
    cmp r12, r13
    jae compile_done

skip_separators:
    cmp r12, r13
    jae compile_done
    cmp byte ptr [r12], 0x20
    ja token_start
    inc r12
    jmp skip_separators

token_start:
    mov rbx, r12

scan_token:
    cmp r12, r13
    jae token_end
    cmp byte ptr [r12], 0x20
    jbe token_end
    inc r12
    jmp scan_token

token_end:
    mov r14, r12
    sub r14, rbx
    cmp r14, 1
    je compile_length_one
    cmp r14, 3
    je compile_length_three
    cmp r14, 4
    je compile_length_four
    jmp compile_number

compile_length_one:
    mov al, byte ptr [rbx]
    cmp al, '+'
    je compile_add
    cmp al, '-'
    je compile_sub
    cmp al, '*'
    je compile_mul
    cmp al, '/'
    je compile_div
    cmp al, '='
    je compile_equal
    cmp al, '.'
    je compile_dot
    jmp compile_number

compile_length_three:
    cmp byte ptr [rbx], 'd'
    jne compile_number
    cmp byte ptr [rbx + 1], 'u'
    jne compile_number
    cmp byte ptr [rbx + 2], 'p'
    jne compile_number
    mov dl, OP_DUP
    jmp emit_word

compile_length_four:
    cmp byte ptr [rbx], 'd'
    je maybe_drop
    cmp byte ptr [rbx], 's'
    je maybe_swap
    cmp byte ptr [rbx], 'o'
    je maybe_over
    jmp compile_number

maybe_drop:
    cmp byte ptr [rbx + 1], 'r'
    jne compile_number
    cmp byte ptr [rbx + 2], 'o'
    jne compile_number
    cmp byte ptr [rbx + 3], 'p'
    jne compile_number
    mov dl, OP_DROP
    jmp emit_word

maybe_swap:
    cmp byte ptr [rbx + 1], 'w'
    jne compile_number
    cmp byte ptr [rbx + 2], 'a'
    jne compile_number
    cmp byte ptr [rbx + 3], 'p'
    jne compile_number
    mov dl, OP_SWAP
    jmp emit_word

maybe_over:
    cmp byte ptr [rbx + 1], 'v'
    jne compile_number
    cmp byte ptr [rbx + 2], 'e'
    jne compile_number
    cmp byte ptr [rbx + 3], 'r'
    jne compile_number
    mov dl, OP_OVER
    jmp emit_word

compile_add:
    mov dl, OP_ADD
    jmp emit_word
compile_sub:
    mov dl, OP_SUB
    jmp emit_word
compile_mul:
    mov dl, OP_MUL
    jmp emit_word
compile_div:
    mov dl, OP_DIV
    jmp emit_word
compile_equal:
    mov dl, OP_EQUAL
    jmp emit_word
compile_dot:
    mov dl, OP_DOT

emit_word:
    lea rax, [rip + code_buffer_end]
    cmp r15, rax
    jae error_program_large
    mov byte ptr [r15], dl
    inc r15
    jmp compile_next

compile_number:
    mov rsi, rbx
    mov rcx, r14
    xor r9d, r9d
    cmp byte ptr [rsi], '-'
    jne number_digits
    mov r9d, 1
    inc rsi
    dec rcx
    jz error_compile

number_digits:
    xor eax, eax

number_loop:
    movzx edx, byte ptr [rsi]
    sub edx, '0'
    cmp edx, 9
    ja error_compile
    imul rax, rax, 10
    jo error_compile
    test r9d, r9d
    jnz number_negative_digit
    add rax, rdx
    jo error_compile
    jmp number_digit_done

number_negative_digit:
    sub rax, rdx
    jo error_compile

number_digit_done:
    inc rsi
    dec rcx
    jnz number_loop

    lea rdx, [r15 + 9]
    lea rcx, [rip + code_buffer_end]
    cmp rdx, rcx
    ja error_program_large
    mov byte ptr [r15], OP_PUSH
    mov qword ptr [r15 + 1], rax
    add r15, 9
    jmp compile_next

compile_done:
    lea rax, [rip + code_buffer_end]
    cmp r15, rax
    jae error_program_large
    mov byte ptr [r15], OP_HALT
    lea r12, [rip + code_buffer]
    lea r14, [rip + data_stack]
    xor r15d, r15d
    jmp execute_next

execute_next:
    movzx eax, byte ptr [r12]
    inc r12
    cmp al, OP_HALT
    je exit_success
    cmp al, OP_PUSH
    je execute_push
    cmp al, OP_ADD
    je execute_add
    cmp al, OP_SUB
    je execute_sub
    cmp al, OP_MUL
    je execute_mul
    cmp al, OP_DIV
    je execute_div
    cmp al, OP_DUP
    je execute_dup
    cmp al, OP_DROP
    je execute_drop
    cmp al, OP_SWAP
    je execute_swap
    cmp al, OP_OVER
    je execute_over
    cmp al, OP_EQUAL
    je execute_equal
    cmp al, OP_DOT
    je execute_dot
    jmp error_internal

execute_push:
    cmp r15, STACK_CELLS
    jae error_stack_overflow
    mov rax, qword ptr [r12]
    add r12, 8
    mov qword ptr [r14 + r15 * 8], rax
    inc r15
    jmp execute_next

execute_add:
    cmp r15, 2
    jb error_stack_underflow
    mov rax, qword ptr [r14 + r15 * 8 - 16]
    add rax, qword ptr [r14 + r15 * 8 - 8]
    jo error_arithmetic
    mov qword ptr [r14 + r15 * 8 - 16], rax
    dec r15
    jmp execute_next

execute_sub:
    cmp r15, 2
    jb error_stack_underflow
    mov rax, qword ptr [r14 + r15 * 8 - 16]
    sub rax, qword ptr [r14 + r15 * 8 - 8]
    jo error_arithmetic
    mov qword ptr [r14 + r15 * 8 - 16], rax
    dec r15
    jmp execute_next

execute_mul:
    cmp r15, 2
    jb error_stack_underflow
    mov rax, qword ptr [r14 + r15 * 8 - 16]
    imul rax, qword ptr [r14 + r15 * 8 - 8]
    jo error_arithmetic
    mov qword ptr [r14 + r15 * 8 - 16], rax
    dec r15
    jmp execute_next

execute_div:
    cmp r15, 2
    jb error_stack_underflow
    mov rbx, qword ptr [r14 + r15 * 8 - 8]
    test rbx, rbx
    jz error_division_zero
    mov rax, qword ptr [r14 + r15 * 8 - 16]
    mov rcx, 0x8000000000000000
    cmp rax, rcx
    jne division_safe
    cmp rbx, -1
    je error_arithmetic

division_safe:
    cqo
    idiv rbx
    mov qword ptr [r14 + r15 * 8 - 16], rax
    dec r15
    jmp execute_next

execute_dup:
    cmp r15, 1
    jb error_stack_underflow
    cmp r15, STACK_CELLS
    jae error_stack_overflow
    mov rax, qword ptr [r14 + r15 * 8 - 8]
    mov qword ptr [r14 + r15 * 8], rax
    inc r15
    jmp execute_next

execute_drop:
    cmp r15, 1
    jb error_stack_underflow
    dec r15
    jmp execute_next

execute_swap:
    cmp r15, 2
    jb error_stack_underflow
    mov rax, qword ptr [r14 + r15 * 8 - 16]
    mov rdx, qword ptr [r14 + r15 * 8 - 8]
    mov qword ptr [r14 + r15 * 8 - 16], rdx
    mov qword ptr [r14 + r15 * 8 - 8], rax
    jmp execute_next

execute_over:
    cmp r15, 2
    jb error_stack_underflow
    cmp r15, STACK_CELLS
    jae error_stack_overflow
    mov rax, qword ptr [r14 + r15 * 8 - 16]
    mov qword ptr [r14 + r15 * 8], rax
    inc r15
    jmp execute_next

execute_equal:
    cmp r15, 2
    jb error_stack_underflow
    mov rax, qword ptr [r14 + r15 * 8 - 16]
    cmp rax, qword ptr [r14 + r15 * 8 - 8]
    sete al
    movzx rax, al
    mov qword ptr [r14 + r15 * 8 - 16], rax
    dec r15
    jmp execute_next

execute_dot:
    cmp r15, 1
    jb error_stack_underflow
    dec r15
    mov rax, qword ptr [r14 + r15 * 8]
    call print_integer
    jmp execute_next

print_integer:
    lea rsi, [rip + output_buffer_end]
    dec rsi
    mov byte ptr [rsi], 10
    mov ecx, 1
    xor r8d, r8d
    test rax, rax
    jz print_zero
    js print_negative
    neg rax
    jmp print_digits

print_negative:
    mov r8d, 1

print_digits:
    mov ebx, 10

print_digit_loop:
    cqo
    idiv rbx
    neg edx
    add dl, '0'
    dec rsi
    mov byte ptr [rsi], dl
    inc rcx
    test rax, rax
    jnz print_digit_loop
    test r8d, r8d
    jz write_number
    dec rsi
    mov byte ptr [rsi], '-'
    inc rcx
    jmp write_number

print_zero:
    dec rsi
    mov byte ptr [rsi], '0'
    inc rcx

write_number:
    mov rdx, rcx

write_number_loop:
    test rdx, rdx
    jz write_number_done
    mov eax, SYS_write
    mov edi, 1
    syscall
    test rax, rax
    jle error_internal
    add rsi, rax
    sub rdx, rax
    jmp write_number_loop

write_number_done:
    ret

error_read:
    lea rsi, [rip + message_read]
    mov edx, OFFSET FLAT:message_read_length
    mov r8d, 1
    jmp fail
error_compile:
    lea rsi, [rip + message_compile]
    mov edx, OFFSET FLAT:message_compile_length
    mov r8d, 2
    jmp fail
error_stack_underflow:
    lea rsi, [rip + message_underflow]
    mov edx, OFFSET FLAT:message_underflow_length
    mov r8d, 3
    jmp fail
error_stack_overflow:
    lea rsi, [rip + message_overflow]
    mov edx, OFFSET FLAT:message_overflow_length
    mov r8d, 4
    jmp fail
error_division_zero:
    lea rsi, [rip + message_division]
    mov edx, OFFSET FLAT:message_division_length
    mov r8d, 5
    jmp fail
error_input_large:
    lea rsi, [rip + message_input]
    mov edx, OFFSET FLAT:message_input_length
    mov r8d, 6
    jmp fail
error_arithmetic:
    lea rsi, [rip + message_arithmetic]
    mov edx, OFFSET FLAT:message_arithmetic_length
    mov r8d, 7
    jmp fail
error_program_large:
    lea rsi, [rip + message_program]
    mov edx, OFFSET FLAT:message_program_length
    mov r8d, 8
    jmp fail
error_internal:
    lea rsi, [rip + message_internal]
    mov edx, OFFSET FLAT:message_internal_length
    mov r8d, 9

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
message_underflow:
    .ascii "stack underflow\n"
.equ message_underflow_length, . - message_underflow
message_overflow:
    .ascii "stack overflow\n"
.equ message_overflow_length, . - message_overflow
message_division:
    .ascii "division by zero\n"
.equ message_division_length, . - message_division
message_input:
    .ascii "input too large\n"
.equ message_input_length, . - message_input
message_arithmetic:
    .ascii "arithmetic overflow\n"
.equ message_arithmetic_length, . - message_arithmetic
message_program:
    .ascii "program too large\n"
.equ message_program_length, . - message_program
message_internal:
    .ascii "internal bytecode error\n"
.equ message_internal_length, . - message_internal

.section .bss
.balign 16
input_buffer:
    .skip INPUT_CAPACITY
.balign 16
code_buffer:
    .skip CODE_CAPACITY
code_buffer_end:
.balign 16
data_stack:
    .skip STACK_CELLS * 8
.balign 16
output_buffer:
    .skip 32
output_buffer_end:

.section .note.GNU-stack,"",@progbits
