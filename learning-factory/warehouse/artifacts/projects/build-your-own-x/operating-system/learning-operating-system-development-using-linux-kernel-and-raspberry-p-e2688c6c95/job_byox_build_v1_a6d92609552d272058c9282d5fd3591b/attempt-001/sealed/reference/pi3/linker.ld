ENTRY(_start)

SECTIONS
{
    . = 0x80000;
    .text : {
        KEEP(*(.text.boot))
        *(.text*)
    }
    .rodata : { *(.rodata*) }
    .data : { *(.data*) }
    .bss (NOLOAD) : {
        __bss_start = .;
        *(.bss*)
        *(COMMON)
        __bss_end = .;
    }
    . = ALIGN(16);
    . += 0x4000;
    __stack_top = .;
    /DISCARD/ : { *(.comment*) *(.note*) *(.eh_frame*) }
}
