.set MULTIBOOT_MAGIC, 0x1badb002
.set MULTIBOOT_FLAGS, 0x00000003
.set MULTIBOOT_CHECKSUM, -(MULTIBOOT_MAGIC + MULTIBOOT_FLAGS)

.section .multiboot, "a"
.align 4
.long MULTIBOOT_MAGIC
.long MULTIBOOT_FLAGS
.long MULTIBOOT_CHECKSUM

.section .bss, "aw", @nobits
.align 16
stack_bottom:
.skip 16384
stack_top:

.section .text
.global _start
.type _start, @function
.extern kernel_main
_start:
    movl $stack_top, %esp
    xorl %ebp, %ebp
    call kernel_main
1:
    cli
    hlt
    jmp 1b
.size _start, . - _start

.section .note.GNU-stack, "", @progbits
