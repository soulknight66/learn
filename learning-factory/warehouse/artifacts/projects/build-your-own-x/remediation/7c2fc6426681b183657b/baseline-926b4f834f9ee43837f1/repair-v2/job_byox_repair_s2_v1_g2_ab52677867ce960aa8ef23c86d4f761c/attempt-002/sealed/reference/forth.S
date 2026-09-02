.intel_syntax noprefix

/*
 * Cinder: an independently written, freestanding x86-64 Linux Forth.
 * The implementation uses fixed storage, Linux syscalls, and a cell-threaded VM.
 */

.equ SYS_read, 0
.equ SYS_write, 1
.equ SYS_exit, 60

.equ INPUT_LIMIT, 65536
.equ INPUT_STORAGE, 65537
.equ DATA_CAPACITY, 256
.equ USER_CAPACITY, 64
.equ NAME_CAPACITY, 32
.equ CODE_CELLS, 8192
.equ PATCH_CAPACITY, 64
.equ RETURN_CAPACITY, 256
.equ VM_FUEL, 1000000

.equ OP_RET, 0
.equ OP_LIT, 1
.equ OP_CALL, 2
.equ OP_JMP, 3
.equ OP_JZ, 4

.equ OP_ADD, 10
.equ OP_SUB, 11
.equ OP_MUL, 12
.equ OP_DIV, 13
.equ OP_MOD, 14
.equ OP_EQ, 20
.equ OP_LT, 21
.equ OP_GT, 22
.equ OP_ZERO_EQ, 23
.equ OP_AND, 30
.equ OP_OR, 31
.equ OP_XOR, 32
.equ OP_INVERT, 33
.equ OP_DUP, 40
.equ OP_DROP, 41
.equ OP_SWAP, 42
.equ OP_OVER, 43
.equ OP_ROT, 44
.equ OP_DEPTH, 45
.equ OP_DOT, 50
.equ OP_DOTS, 51
.equ OP_EMIT, 52
.equ OP_CR, 53

.equ PATCH_IF, 1
.equ PATCH_ELSE, 2

.section .rodata
name_add:       .ascii "+"
name_sub:       .ascii "-"
name_mul:       .ascii "*"
name_div:       .ascii "/"
name_mod:       .ascii "mod"
name_eq:        .ascii "="
name_lt:        .ascii "<"
name_gt:        .ascii ">"
name_zero_eq:   .ascii "0="
name_and:       .ascii "and"
name_or:        .ascii "or"
name_xor:       .ascii "xor"
name_invert:    .ascii "invert"
name_dup:       .ascii "dup"
name_drop:      .ascii "drop"
name_swap:      .ascii "swap"
name_over:      .ascii "over"
name_rot:       .ascii "rot"
name_depth:     .ascii "depth"
name_dot:       .ascii "."
name_dots:      .ascii ".s"
name_emit:      .ascii "emit"
name_cr:        .ascii "cr"

.align 8
builtin_table:
    .quad name_add,       1, OP_ADD
    .quad name_sub,       1, OP_SUB
    .quad name_mul,       1, OP_MUL
    .quad name_div,       1, OP_DIV
    .quad name_mod,       3, OP_MOD
    .quad name_eq,        1, OP_EQ
    .quad name_lt,        1, OP_LT
    .quad name_gt,        1, OP_GT
    .quad name_zero_eq,   2, OP_ZERO_EQ
    .quad name_and,       3, OP_AND
    .quad name_or,        2, OP_OR
    .quad name_xor,       3, OP_XOR
    .quad name_invert,    6, OP_INVERT
    .quad name_dup,       3, OP_DUP
    .quad name_drop,      4, OP_DROP
    .quad name_swap,      4, OP_SWAP
    .quad name_over,      4, OP_OVER
    .quad name_rot,       3, OP_ROT
    .quad name_depth,     5, OP_DEPTH
    .quad name_dot,       1, OP_DOT
    .quad name_dots,      2, OP_DOTS
    .quad name_emit,      4, OP_EMIT
    .quad name_cr,        2, OP_CR
.equ BUILTIN_COUNT, (. - builtin_table) / 24

word_colon:     .ascii ":"
word_semicolon: .ascii ";"
word_if:        .ascii "if"
word_else:      .ascii "else"
word_then:      .ascii "then"
word_recurse:   .ascii "recurse"

.align 8
control_table:
    .quad word_colon,     1
    .quad word_semicolon, 1
    .quad word_if,        2
    .quad word_else,      4
    .quad word_then,      4
    .quad word_recurse,   7
.equ CONTROL_COUNT, (. - control_table) / 16

err_read:           .ascii "error: input read failed\n"
.equ err_read_len, . - err_read
err_input_size:     .ascii "error: input exceeds 65536 bytes\n"
.equ err_input_size_len, . - err_input_size
err_output:         .ascii "error: output write failed\n"
.equ err_output_len, . - err_output
err_unknown:        .ascii "error: unknown token\n"
.equ err_unknown_len, . - err_unknown
err_number:         .ascii "error: integer out of range\n"
.equ err_number_len, . - err_number
err_underflow:      .ascii "error: data stack underflow\n"
.equ err_underflow_len, . - err_underflow
err_overflow:       .ascii "error: data stack overflow\n"
.equ err_overflow_len, . - err_overflow
err_div_zero:       .ascii "error: division by zero\n"
.equ err_div_zero_len, . - err_div_zero
err_div_overflow:   .ascii "error: signed division overflow\n"
.equ err_div_overflow_len, . - err_div_overflow
err_definition:     .ascii "error: invalid definition\n"
.equ err_definition_len, . - err_definition
err_unclosed:       .ascii "error: unterminated definition\n"
.equ err_unclosed_len, . - err_unclosed
err_compile:        .ascii "error: malformed compile-time control flow\n"
.equ err_compile_len, . - err_compile
err_dictionary:     .ascii "error: user dictionary full\n"
.equ err_dictionary_len, . - err_dictionary
err_code:           .ascii "error: compiled code arena full\n"
.equ err_code_len, . - err_code
err_patch:          .ascii "error: control-flow nesting limit exceeded\n"
.equ err_patch_len, . - err_patch
err_return:         .ascii "error: return stack overflow\n"
.equ err_return_len, . - err_return
err_fuel:           .ascii "error: VM instruction limit exceeded\n"
.equ err_fuel_len, . - err_fuel
err_internal:       .ascii "error: invalid VM instruction\n"
.equ err_internal_len, . - err_internal

.section .bss
.align 16
input_buffer:       .skip INPUT_STORAGE
.align 8
input_length:       .skip 8
scan_cursor:        .skip 8
token_pointer:      .skip 8
token_length:       .skip 8

.align 16
data_stack:         .skip DATA_CAPACITY * 8
data_depth:         .skip 8

.align 16
user_names:         .skip USER_CAPACITY * NAME_CAPACITY
user_name_lengths:  .skip USER_CAPACITY * 8
user_bodies:        .skip USER_CAPACITY * 8
user_count:         .skip 8
current_word:       .skip 8
compile_mode:       .skip 8

.align 16
code_arena:         .skip CODE_CELLS * 8
code_end:
code_here:          .skip 8

.align 16
patch_addresses:    .skip PATCH_CAPACITY * 8
patch_kinds:        .skip PATCH_CAPACITY * 8
patch_depth:        .skip 8

.align 16
return_stack:       .skip RETURN_CAPACITY * 8
return_depth:       .skip 8
vm_ip:              .skip 8
vm_steps:           .skip 8

.align 16
number_buffer:      .skip 32
character_buffer:   .skip 1

.section .text
.global _start
.type _start, @function
_start:
    lea rax, [rip + code_arena]
    mov qword ptr [rip + code_here], rax
    call read_input

.main_loop:
    call next_token
    test rcx, rcx
    jz .end_of_input
    mov qword ptr [rip + token_pointer], rax
    mov qword ptr [rip + token_length], rdx
    call process_token
    jmp .main_loop

.end_of_input:
    cmp qword ptr [rip + compile_mode], 0
    jne fatal_unclosed
    mov eax, SYS_exit
    xor edi, edi
    syscall
.size _start, . - _start

/* Read one bounded source stream. */
.type read_input, @function
read_input:
    xor r12d, r12d
.read_more:
    cmp r12, INPUT_STORAGE
    jae fatal_input_size
    xor eax, eax
    xor edi, edi
    lea rsi, [rip + input_buffer]
    add rsi, r12
    mov edx, INPUT_STORAGE
    sub rdx, r12
    syscall
    test rax, rax
    jz .read_done
    js .read_error
    add r12, rax
    cmp r12, INPUT_LIMIT
    ja fatal_input_size
    jmp .read_more
.read_error:
    cmp rax, -4
    je .read_more
    jmp fatal_read
.read_done:
    mov qword ptr [rip + input_length], r12
    mov qword ptr [rip + scan_cursor], 0
    ret

/* Return RAX=token pointer, RDX=length, RCX=1; RCX=0 means EOF. */
.type next_token, @function
next_token:
    mov r8, qword ptr [rip + scan_cursor]
    mov r9, qword ptr [rip + input_length]
    lea r10, [rip + input_buffer]
.seek:
    cmp r8, r9
    jae .token_eof
    movzx eax, byte ptr [r10 + r8]
    cmp al, 32
    jbe .skip_byte
    cmp al, '#'
    jne .token_start
.skip_comment:
    inc r8
    cmp r8, r9
    jae .token_eof_store
    cmp byte ptr [r10 + r8], 10
    jne .skip_comment
    jmp .seek
.skip_byte:
    inc r8
    jmp .seek
.token_start:
    mov r11, r8
.token_scan:
    inc r8
    cmp r8, r9
    jae .token_ready
    movzx eax, byte ptr [r10 + r8]
    cmp al, 32
    ja .token_scan
.token_ready:
    mov qword ptr [rip + scan_cursor], r8
    lea rax, [r10 + r11]
    mov rdx, r8
    sub rdx, r11
    mov ecx, 1
    ret
.token_eof_store:
    mov qword ptr [rip + scan_cursor], r8
.token_eof:
    xor eax, eax
    xor edx, edx
    xor ecx, ecx
    ret

/* Compare byte strings RDI/RSI and RDX/RCX. */
.type bytes_equal, @function
bytes_equal:
    cmp rsi, rcx
    jne .bytes_no
    xor r8d, r8d
.bytes_loop:
    cmp r8, rsi
    jae .bytes_yes
    movzx eax, byte ptr [rdi + r8]
    cmp al, byte ptr [rdx + r8]
    jne .bytes_no
    inc r8
    jmp .bytes_loop
.bytes_yes:
    mov eax, 1
    ret
.bytes_no:
    xor eax, eax
    ret

/* Lookup primitive: RDX=1 and RAX=opcode on success. */
.type lookup_builtin, @function
lookup_builtin:
    mov r8, rdi
    mov r9, rsi
    lea r10, [rip + builtin_table]
    mov r11d, BUILTIN_COUNT
.builtin_entry:
    cmp r9, qword ptr [r10 + 8]
    jne .builtin_next
    mov rdi, qword ptr [r10]
    xor ecx, ecx
.builtin_bytes:
    cmp rcx, r9
    jae .builtin_found
    movzx eax, byte ptr [r8 + rcx]
    cmp al, byte ptr [rdi + rcx]
    jne .builtin_next
    inc rcx
    jmp .builtin_bytes
.builtin_found:
    mov rax, qword ptr [r10 + 16]
    mov edx, 1
    ret
.builtin_next:
    add r10, 24
    dec r11
    jnz .builtin_entry
    xor eax, eax
    xor edx, edx
    ret

/* Lookup completed user word: RDX=1 and RAX=index on success. */
.type lookup_user, @function
lookup_user:
    mov r8, rdi
    mov r9, rsi
    xor r10d, r10d
    mov r11, qword ptr [rip + user_count]
.user_entry:
    cmp r10, r11
    jae .user_missing
    lea rdi, [rip + user_name_lengths]
    cmp r9, qword ptr [rdi + r10 * 8]
    jne .user_next
    mov rax, r10
    shl rax, 5
    lea rdi, [rip + user_names]
    add rdi, rax
    xor ecx, ecx
.user_bytes:
    cmp rcx, r9
    jae .user_found
    movzx eax, byte ptr [r8 + rcx]
    cmp al, byte ptr [rdi + rcx]
    jne .user_next
    inc rcx
    jmp .user_bytes
.user_found:
    mov rax, r10
    mov edx, 1
    ret
.user_next:
    inc r10
    jmp .user_entry
.user_missing:
    xor eax, eax
    xor edx, edx
    ret

/* Return EAX=1 for any reserved compiler/control token. */
.type lookup_control, @function
lookup_control:
    mov r8, rdi
    mov r9, rsi
    lea r10, [rip + control_table]
    mov r11d, CONTROL_COUNT
.control_entry:
    cmp r9, qword ptr [r10 + 8]
    jne .control_next
    mov rdi, qword ptr [r10]
    xor ecx, ecx
.control_bytes:
    cmp rcx, r9
    jae .control_found
    movzx eax, byte ptr [r8 + rcx]
    cmp al, byte ptr [rdi + rcx]
    jne .control_next
    inc rcx
    jmp .control_bytes
.control_found:
    mov eax, 1
    ret
.control_next:
    add r10, 16
    dec r11
    jnz .control_entry
    xor eax, eax
    ret

/*
 * Parse a signed decimal. RDX=0 means not numeric, 1 means valid, and 2
 * means a syntactically numeric token outside int64. RAX holds a valid cell.
 */
.type parse_number, @function
parse_number:
    test rsi, rsi
    jz .number_not
    mov r8, rdi
    mov r9, rsi
    xor r10d, r10d
    cmp byte ptr [r8], '-'
    jne .number_digits_begin
    mov r10d, 1
    inc r8
    dec r9
    jz .number_not
.number_digits_begin:
    /* Classify the complete token before doing range-sensitive arithmetic. */
    xor ecx, ecx
.number_shape_loop:
    cmp rcx, r9
    jae .number_shape_valid
    movzx edx, byte ptr [r8 + rcx]
    sub edx, '0'
    cmp edx, 9
    ja .number_not
    inc rcx
    jmp .number_shape_loop
.number_shape_valid:
    xor eax, eax
    xor ecx, ecx
.number_digit_loop:
    cmp rcx, r9
    jae .number_done
    movzx edx, byte ptr [r8 + rcx]
    sub edx, '0'
    movabs rdi, 922337203685477580
    cmp rax, rdi
    ja .number_overflow
    jb .number_accumulate
    test r10d, r10d
    jnz .number_negative_edge
    cmp edx, 7
    ja .number_overflow
    jmp .number_accumulate
.number_negative_edge:
    cmp edx, 8
    ja .number_overflow
.number_accumulate:
    imul rax, rax, 10
    add rax, rdx
    inc rcx
    jmp .number_digit_loop
.number_done:
    test r10d, r10d
    jz .number_valid
    neg rax
.number_valid:
    mov edx, 1
    ret
.number_overflow:
    xor eax, eax
    mov edx, 2
    ret
.number_not:
    xor eax, eax
    xor edx, edx
    ret

/* Dispatch a token using the explicit interpreter/compiler mode. */
.type process_token, @function
process_token:
    cmp qword ptr [rip + compile_mode], 0
    jne compile_token

.type interpret_token, @function
interpret_token:
    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    lea rdx, [rip + word_colon]
    mov ecx, 1
    call bytes_equal
    test eax, eax
    jnz begin_definition

    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    call lookup_control
    test eax, eax
    jnz fatal_compile

    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    call parse_number
    cmp edx, 1
    je push_rax
    cmp edx, 2
    je fatal_number

    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    call lookup_builtin
    test edx, edx
    jnz .interpret_primitive

    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    call lookup_user
    test edx, edx
    jnz .interpret_user
    jmp fatal_unknown
.interpret_primitive:
    mov rdi, rax
    jmp execute_primitive
.interpret_user:
    mov rdi, rax
    jmp execute_word

/* Consume and validate the name after ':'. */
.type begin_definition, @function
begin_definition:
    mov rax, qword ptr [rip + user_count]
    cmp rax, USER_CAPACITY
    jae fatal_dictionary
    call next_token
    test rcx, rcx
    jz fatal_definition
    mov qword ptr [rip + token_pointer], rax
    mov qword ptr [rip + token_length], rdx
    test rdx, rdx
    jz fatal_definition
    cmp rdx, NAME_CAPACITY - 1
    ja fatal_definition

    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    call parse_number
    test edx, edx
    jnz fatal_definition

    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    call lookup_control
    test eax, eax
    jnz fatal_definition
    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    call lookup_builtin
    test edx, edx
    jnz fatal_definition
    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    call lookup_user
    test edx, edx
    jnz fatal_definition

    mov r10, qword ptr [rip + user_count]
    lea rdi, [rip + user_name_lengths]
    mov rax, qword ptr [rip + token_length]
    mov qword ptr [rdi + r10 * 8], rax
    lea rdi, [rip + user_bodies]
    mov rax, qword ptr [rip + code_here]
    mov qword ptr [rdi + r10 * 8], rax

    mov rax, r10
    shl rax, 5
    lea rdi, [rip + user_names]
    add rdi, rax
    mov rsi, qword ptr [rip + token_pointer]
    mov rcx, qword ptr [rip + token_length]
    rep movsb

    mov qword ptr [rip + current_word], r10
    mov qword ptr [rip + patch_depth], 0
    mov qword ptr [rip + compile_mode], 1
    ret

/* Compiler token dispatch. */
.type compile_token, @function
compile_token:
    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    lea rdx, [rip + word_semicolon]
    mov ecx, 1
    call bytes_equal
    test eax, eax
    jnz finish_definition

    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    lea rdx, [rip + word_if]
    mov ecx, 2
    call bytes_equal
    test eax, eax
    jnz compile_if

    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    lea rdx, [rip + word_else]
    mov ecx, 4
    call bytes_equal
    test eax, eax
    jnz compile_else

    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    lea rdx, [rip + word_then]
    mov ecx, 4
    call bytes_equal
    test eax, eax
    jnz compile_then

    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    lea rdx, [rip + word_recurse]
    mov ecx, 7
    call bytes_equal
    test eax, eax
    jnz compile_recurse

    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    call lookup_control
    test eax, eax
    jnz fatal_compile

    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    call parse_number
    cmp edx, 1
    je compile_literal
    cmp edx, 2
    je fatal_number

    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    call lookup_builtin
    test edx, edx
    jnz compile_primitive

    mov rdi, qword ptr [rip + token_pointer]
    mov rsi, qword ptr [rip + token_length]
    call lookup_user
    test edx, edx
    jnz compile_call
    jmp fatal_unknown

finish_definition:
    cmp qword ptr [rip + patch_depth], 0
    jne fatal_compile
    mov eax, OP_RET
    call emit_cell
    inc qword ptr [rip + user_count]
    mov qword ptr [rip + compile_mode], 0
    ret

compile_literal:
    mov r12, rax
    mov eax, OP_LIT
    call emit_cell
    mov rax, r12
    jmp emit_cell

compile_primitive:
    jmp emit_cell

compile_call:
    mov r12, rax
    mov eax, OP_CALL
    call emit_cell
    mov rax, r12
    jmp emit_cell

compile_recurse:
    mov eax, OP_CALL
    call emit_cell
    mov rax, qword ptr [rip + current_word]
    jmp emit_cell

compile_if:
    mov r12, qword ptr [rip + patch_depth]
    cmp r12, PATCH_CAPACITY
    jae fatal_patch
    mov eax, OP_JZ
    call emit_cell
    mov r13, qword ptr [rip + code_here]
    xor eax, eax
    call emit_cell
    lea rax, [rip + patch_addresses]
    mov qword ptr [rax + r12 * 8], r13
    lea rax, [rip + patch_kinds]
    mov qword ptr [rax + r12 * 8], PATCH_IF
    inc r12
    mov qword ptr [rip + patch_depth], r12
    ret

compile_else:
    mov r12, qword ptr [rip + patch_depth]
    test r12, r12
    jz fatal_compile
    dec r12
    lea rax, [rip + patch_kinds]
    cmp qword ptr [rax + r12 * 8], PATCH_IF
    jne fatal_compile
    lea rax, [rip + patch_addresses]
    mov r14, qword ptr [rax + r12 * 8]
    mov eax, OP_JMP
    call emit_cell
    mov r13, qword ptr [rip + code_here]
    xor eax, eax
    call emit_cell
    mov rax, qword ptr [rip + code_here]
    mov qword ptr [r14], rax
    lea rax, [rip + patch_addresses]
    mov qword ptr [rax + r12 * 8], r13
    lea rax, [rip + patch_kinds]
    mov qword ptr [rax + r12 * 8], PATCH_ELSE
    ret

compile_then:
    mov r12, qword ptr [rip + patch_depth]
    test r12, r12
    jz fatal_compile
    dec r12
    lea rax, [rip + patch_kinds]
    mov r13, qword ptr [rax + r12 * 8]
    cmp r13, PATCH_IF
    je .then_kind_ok
    cmp r13, PATCH_ELSE
    jne fatal_compile
.then_kind_ok:
    lea rax, [rip + patch_addresses]
    mov r14, qword ptr [rax + r12 * 8]
    mov rax, qword ptr [rip + code_here]
    mov qword ptr [r14], rax
    mov qword ptr [rip + patch_depth], r12
    ret

/* Append RAX to the bounded cell arena. */
.type emit_cell, @function
emit_cell:
    mov rdx, qword ptr [rip + code_here]
    lea rcx, [rip + code_end]
    cmp rdx, rcx
    jae fatal_code
    mov qword ptr [rdx], rax
    add rdx, 8
    mov qword ptr [rip + code_here], rdx
    ret

/* Push RAX onto the checked data stack. */
.type push_rax, @function
push_rax:
    mov rdx, qword ptr [rip + data_depth]
    cmp rdx, DATA_CAPACITY
    jae fatal_overflow
    lea rcx, [rip + data_stack]
    mov qword ptr [rcx + rdx * 8], rax
    inc rdx
    mov qword ptr [rip + data_depth], rdx
    ret

/* Execute a completed user word through the bounded VM. */
.type execute_word, @function
execute_word:
    cmp rdi, qword ptr [rip + user_count]
    jae fatal_internal
    lea rax, [rip + user_bodies]
    mov rax, qword ptr [rax + rdi * 8]
    mov qword ptr [rip + vm_ip], rax
    mov qword ptr [rip + return_depth], 0
    mov qword ptr [rip + vm_steps], VM_FUEL
.vm_loop:
    cmp qword ptr [rip + vm_steps], 0
    je fatal_fuel
    dec qword ptr [rip + vm_steps]
    mov r8, qword ptr [rip + vm_ip]
    mov rdi, qword ptr [r8]
    add r8, 8
    mov qword ptr [rip + vm_ip], r8
    cmp rdi, OP_RET
    je .vm_return
    cmp rdi, OP_LIT
    je .vm_literal
    cmp rdi, OP_CALL
    je .vm_call
    cmp rdi, OP_JMP
    je .vm_jump
    cmp rdi, OP_JZ
    je .vm_jump_zero
    call execute_primitive
    jmp .vm_loop

.vm_return:
    mov rcx, qword ptr [rip + return_depth]
    test rcx, rcx
    jz .vm_done
    dec rcx
    mov qword ptr [rip + return_depth], rcx
    lea rax, [rip + return_stack]
    mov rax, qword ptr [rax + rcx * 8]
    mov qword ptr [rip + vm_ip], rax
    jmp .vm_loop
.vm_done:
    ret

.vm_literal:
    mov r8, qword ptr [rip + vm_ip]
    mov rax, qword ptr [r8]
    add r8, 8
    mov qword ptr [rip + vm_ip], r8
    call push_rax
    jmp .vm_loop

.vm_call:
    mov r8, qword ptr [rip + vm_ip]
    mov rdi, qword ptr [r8]
    add r8, 8
    mov qword ptr [rip + vm_ip], r8
    cmp rdi, qword ptr [rip + user_count]
    jae fatal_internal
    mov rcx, qword ptr [rip + return_depth]
    cmp rcx, RETURN_CAPACITY
    jae fatal_return
    lea rax, [rip + return_stack]
    mov qword ptr [rax + rcx * 8], r8
    inc rcx
    mov qword ptr [rip + return_depth], rcx
    lea rax, [rip + user_bodies]
    mov rax, qword ptr [rax + rdi * 8]
    mov qword ptr [rip + vm_ip], rax
    jmp .vm_loop

.vm_jump:
    mov r8, qword ptr [rip + vm_ip]
    mov rax, qword ptr [r8]
    mov qword ptr [rip + vm_ip], rax
    jmp .vm_loop

.vm_jump_zero:
    mov r8, qword ptr [rip + vm_ip]
    mov r9, qword ptr [r8]
    add r8, 8
    mov qword ptr [rip + vm_ip], r8
    mov rcx, qword ptr [rip + data_depth]
    test rcx, rcx
    jz fatal_underflow
    dec rcx
    lea rax, [rip + data_stack]
    mov rax, qword ptr [rax + rcx * 8]
    mov qword ptr [rip + data_depth], rcx
    test rax, rax
    jnz .vm_loop
    mov qword ptr [rip + vm_ip], r9
    jmp .vm_loop

/* Primitive dispatcher. Each branch returns directly to its caller. */
.type execute_primitive, @function
execute_primitive:
    cmp rdi, OP_ADD
    je prim_add
    cmp rdi, OP_SUB
    je prim_sub
    cmp rdi, OP_MUL
    je prim_mul
    cmp rdi, OP_DIV
    je prim_div
    cmp rdi, OP_MOD
    je prim_mod
    cmp rdi, OP_EQ
    je prim_eq
    cmp rdi, OP_LT
    je prim_lt
    cmp rdi, OP_GT
    je prim_gt
    cmp rdi, OP_ZERO_EQ
    je prim_zero_eq
    cmp rdi, OP_AND
    je prim_and
    cmp rdi, OP_OR
    je prim_or
    cmp rdi, OP_XOR
    je prim_xor
    cmp rdi, OP_INVERT
    je prim_invert
    cmp rdi, OP_DUP
    je prim_dup
    cmp rdi, OP_DROP
    je prim_drop
    cmp rdi, OP_SWAP
    je prim_swap
    cmp rdi, OP_OVER
    je prim_over
    cmp rdi, OP_ROT
    je prim_rot
    cmp rdi, OP_DEPTH
    je prim_depth
    cmp rdi, OP_DOT
    je prim_dot
    cmp rdi, OP_DOTS
    je prim_dots
    cmp rdi, OP_EMIT
    je prim_emit
    cmp rdi, OP_CR
    je prim_cr
    jmp fatal_internal

prim_add:
    mov rcx, qword ptr [rip + data_depth]
    cmp rcx, 2
    jb fatal_underflow
    lea rdx, [rip + data_stack]
    mov rax, qword ptr [rdx + rcx * 8 - 16]
    add rax, qword ptr [rdx + rcx * 8 - 8]
    mov qword ptr [rdx + rcx * 8 - 16], rax
    dec rcx
    mov qword ptr [rip + data_depth], rcx
    ret

prim_sub:
    mov rcx, qword ptr [rip + data_depth]
    cmp rcx, 2
    jb fatal_underflow
    lea rdx, [rip + data_stack]
    mov rax, qword ptr [rdx + rcx * 8 - 16]
    sub rax, qword ptr [rdx + rcx * 8 - 8]
    mov qword ptr [rdx + rcx * 8 - 16], rax
    dec rcx
    mov qword ptr [rip + data_depth], rcx
    ret

prim_mul:
    mov rcx, qword ptr [rip + data_depth]
    cmp rcx, 2
    jb fatal_underflow
    lea rdx, [rip + data_stack]
    mov rax, qword ptr [rdx + rcx * 8 - 16]
    imul rax, qword ptr [rdx + rcx * 8 - 8]
    mov qword ptr [rdx + rcx * 8 - 16], rax
    dec rcx
    mov qword ptr [rip + data_depth], rcx
    ret

prim_div:
    mov r11d, 0
    jmp primitive_division
prim_mod:
    mov r11d, 1
primitive_division:
    mov rcx, qword ptr [rip + data_depth]
    cmp rcx, 2
    jb fatal_underflow
    lea r10, [rip + data_stack]
    mov r8, qword ptr [r10 + rcx * 8 - 8]
    test r8, r8
    jz fatal_div_zero
    mov rax, qword ptr [r10 + rcx * 8 - 16]
    movabs r9, 0x8000000000000000
    cmp rax, r9
    jne .division_safe
    cmp r8, -1
    je fatal_div_overflow
.division_safe:
    cqo
    idiv r8
    test r11d, r11d
    jz .division_store
    mov rax, rdx
.division_store:
    mov qword ptr [r10 + rcx * 8 - 16], rax
    dec rcx
    mov qword ptr [rip + data_depth], rcx
    ret

prim_eq:
    mov r8d, 0
    jmp primitive_compare
prim_lt:
    mov r8d, 1
    jmp primitive_compare
prim_gt:
    mov r8d, 2
primitive_compare:
    mov rcx, qword ptr [rip + data_depth]
    cmp rcx, 2
    jb fatal_underflow
    lea rdx, [rip + data_stack]
    cmp r8d, 0
    je .compare_equal
    cmp r8d, 1
    je .compare_less
    mov rax, qword ptr [rdx + rcx * 8 - 16]
    cmp rax, qword ptr [rdx + rcx * 8 - 8]
    setg al
    jmp .compare_boolean
.compare_equal:
    mov rax, qword ptr [rdx + rcx * 8 - 16]
    cmp rax, qword ptr [rdx + rcx * 8 - 8]
    sete al
    jmp .compare_boolean
.compare_less:
    mov rax, qword ptr [rdx + rcx * 8 - 16]
    cmp rax, qword ptr [rdx + rcx * 8 - 8]
    setl al
.compare_boolean:
    movzx eax, al
    neg rax
    mov qword ptr [rdx + rcx * 8 - 16], rax
    dec rcx
    mov qword ptr [rip + data_depth], rcx
    ret

prim_zero_eq:
    mov rcx, qword ptr [rip + data_depth]
    test rcx, rcx
    jz fatal_underflow
    lea rdx, [rip + data_stack]
    cmp qword ptr [rdx + rcx * 8 - 8], 0
    sete al
    movzx eax, al
    neg rax
    mov qword ptr [rdx + rcx * 8 - 8], rax
    ret

prim_and:
    mov r8d, 0
    jmp primitive_bitwise
prim_or:
    mov r8d, 1
    jmp primitive_bitwise
prim_xor:
    mov r8d, 2
primitive_bitwise:
    mov rcx, qword ptr [rip + data_depth]
    cmp rcx, 2
    jb fatal_underflow
    lea rdx, [rip + data_stack]
    mov rax, qword ptr [rdx + rcx * 8 - 16]
    cmp r8d, 0
    je .bit_and
    cmp r8d, 1
    je .bit_or
    xor rax, qword ptr [rdx + rcx * 8 - 8]
    jmp .bit_store
.bit_and:
    and rax, qword ptr [rdx + rcx * 8 - 8]
    jmp .bit_store
.bit_or:
    or rax, qword ptr [rdx + rcx * 8 - 8]
.bit_store:
    mov qword ptr [rdx + rcx * 8 - 16], rax
    dec rcx
    mov qword ptr [rip + data_depth], rcx
    ret

prim_invert:
    mov rcx, qword ptr [rip + data_depth]
    test rcx, rcx
    jz fatal_underflow
    lea rdx, [rip + data_stack]
    not qword ptr [rdx + rcx * 8 - 8]
    ret

prim_dup:
    mov rcx, qword ptr [rip + data_depth]
    test rcx, rcx
    jz fatal_underflow
    lea rdx, [rip + data_stack]
    mov rax, qword ptr [rdx + rcx * 8 - 8]
    jmp push_rax

prim_drop:
    mov rcx, qword ptr [rip + data_depth]
    test rcx, rcx
    jz fatal_underflow
    dec rcx
    mov qword ptr [rip + data_depth], rcx
    ret

prim_swap:
    mov rcx, qword ptr [rip + data_depth]
    cmp rcx, 2
    jb fatal_underflow
    lea rdx, [rip + data_stack]
    mov rax, qword ptr [rdx + rcx * 8 - 16]
    mov r8, qword ptr [rdx + rcx * 8 - 8]
    mov qword ptr [rdx + rcx * 8 - 16], r8
    mov qword ptr [rdx + rcx * 8 - 8], rax
    ret

prim_over:
    mov rcx, qword ptr [rip + data_depth]
    cmp rcx, 2
    jb fatal_underflow
    lea rdx, [rip + data_stack]
    mov rax, qword ptr [rdx + rcx * 8 - 16]
    jmp push_rax

prim_rot:
    mov rcx, qword ptr [rip + data_depth]
    cmp rcx, 3
    jb fatal_underflow
    lea rdx, [rip + data_stack]
    mov r8, qword ptr [rdx + rcx * 8 - 24]
    mov r9, qword ptr [rdx + rcx * 8 - 16]
    mov r10, qword ptr [rdx + rcx * 8 - 8]
    mov qword ptr [rdx + rcx * 8 - 24], r9
    mov qword ptr [rdx + rcx * 8 - 16], r10
    mov qword ptr [rdx + rcx * 8 - 8], r8
    ret

prim_depth:
    mov rax, qword ptr [rip + data_depth]
    jmp push_rax

prim_dot:
    mov rcx, qword ptr [rip + data_depth]
    test rcx, rcx
    jz fatal_underflow
    dec rcx
    lea rdx, [rip + data_stack]
    mov rax, qword ptr [rdx + rcx * 8]
    mov qword ptr [rip + data_depth], rcx
    mov edi, 10
    jmp print_value

prim_dots:
    xor r12d, r12d
    mov r13, qword ptr [rip + data_depth]
    test r13, r13
    jz prim_cr
.dots_loop:
    lea rdx, [rip + data_stack]
    mov rax, qword ptr [rdx + r12 * 8]
    inc r12
    mov edi, ' '
    cmp r12, r13
    jb .dots_print
    mov edi, 10
.dots_print:
    call print_value
    cmp r12, r13
    jb .dots_loop
    ret

prim_emit:
    mov rcx, qword ptr [rip + data_depth]
    test rcx, rcx
    jz fatal_underflow
    dec rcx
    lea rdx, [rip + data_stack]
    mov rax, qword ptr [rdx + rcx * 8]
    mov qword ptr [rip + data_depth], rcx
    mov byte ptr [rip + character_buffer], al
    mov edi, 1
    lea rsi, [rip + character_buffer]
    mov edx, 1
    jmp write_all

prim_cr:
    mov byte ptr [rip + character_buffer], 10
    mov edi, 1
    lea rsi, [rip + character_buffer]
    mov edx, 1
    jmp write_all

/* Print signed RAX followed by the byte in DIL. */
.type print_value, @function
print_value:
    lea rsi, [rip + number_buffer + 31]
    mov byte ptr [rsi], dil
    mov ecx, 1
    mov r9, rax
    xor r8d, r8d
    test r9, r9
    jns .print_magnitude
    mov r8d, 1
    neg r9
.print_magnitude:
    mov r10d, 10
.print_digit:
    mov rax, r9
    xor edx, edx
    div r10
    add dl, '0'
    dec rsi
    mov byte ptr [rsi], dl
    inc rcx
    mov r9, rax
    test r9, r9
    jnz .print_digit
    test r8d, r8d
    jz .print_write
    dec rsi
    mov byte ptr [rsi], '-'
    inc rcx
.print_write:
    mov edi, 1
    mov rdx, rcx
    jmp write_all

/* Complete a potentially partial write; return to the original caller. */
.type write_all, @function
write_all:
    mov r8, rdx
    mov r9, rsi
    mov r10d, edi
.write_loop:
    test r8, r8
    jz .write_done
    mov eax, SYS_write
    mov edi, r10d
    mov rsi, r9
    mov rdx, r8
    syscall
    test rax, rax
    js .write_error
    jz fatal_output
    add r9, rax
    sub r8, rax
    jmp .write_loop
.write_error:
    cmp rax, -4
    je .write_loop
    jmp fatal_output
.write_done:
    ret

fatal_read:
    lea rsi, [rip + err_read]
    mov edx, err_read_len
    jmp fatal_common
fatal_input_size:
    lea rsi, [rip + err_input_size]
    mov edx, err_input_size_len
    jmp fatal_common
fatal_output:
    lea rsi, [rip + err_output]
    mov edx, err_output_len
    jmp fatal_common
fatal_unknown:
    lea rsi, [rip + err_unknown]
    mov edx, err_unknown_len
    jmp fatal_common
fatal_number:
    lea rsi, [rip + err_number]
    mov edx, err_number_len
    jmp fatal_common
fatal_underflow:
    lea rsi, [rip + err_underflow]
    mov edx, err_underflow_len
    jmp fatal_common
fatal_overflow:
    lea rsi, [rip + err_overflow]
    mov edx, err_overflow_len
    jmp fatal_common
fatal_div_zero:
    lea rsi, [rip + err_div_zero]
    mov edx, err_div_zero_len
    jmp fatal_common
fatal_div_overflow:
    lea rsi, [rip + err_div_overflow]
    mov edx, err_div_overflow_len
    jmp fatal_common
fatal_definition:
    lea rsi, [rip + err_definition]
    mov edx, err_definition_len
    jmp fatal_common
fatal_unclosed:
    lea rsi, [rip + err_unclosed]
    mov edx, err_unclosed_len
    jmp fatal_common
fatal_compile:
    lea rsi, [rip + err_compile]
    mov edx, err_compile_len
    jmp fatal_common
fatal_dictionary:
    lea rsi, [rip + err_dictionary]
    mov edx, err_dictionary_len
    jmp fatal_common
fatal_code:
    lea rsi, [rip + err_code]
    mov edx, err_code_len
    jmp fatal_common
fatal_patch:
    lea rsi, [rip + err_patch]
    mov edx, err_patch_len
    jmp fatal_common
fatal_return:
    lea rsi, [rip + err_return]
    mov edx, err_return_len
    jmp fatal_common
fatal_fuel:
    lea rsi, [rip + err_fuel]
    mov edx, err_fuel_len
    jmp fatal_common
fatal_internal:
    lea rsi, [rip + err_internal]
    mov edx, err_internal_len

/* Best-effort single diagnostic write followed by deterministic status 2. */
fatal_common:
    mov eax, SYS_write
    mov edi, 2
    syscall
    mov eax, SYS_exit
    mov edi, 2
    syscall

.section .note.GNU-stack,"",@progbits
