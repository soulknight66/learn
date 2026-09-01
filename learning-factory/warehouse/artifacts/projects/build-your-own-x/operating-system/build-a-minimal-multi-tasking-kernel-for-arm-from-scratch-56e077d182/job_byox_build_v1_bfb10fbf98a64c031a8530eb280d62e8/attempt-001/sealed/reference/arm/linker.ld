ENTRY(_start)

SECTIONS {
    . = 0x40010000;
    .text : ALIGN(4) {
        KEEP(*(.text.boot))
        *(.text*)
    }
    .rodata : ALIGN(4) { *(.rodata*) }
    .data : ALIGN(4) { *(.data*) }
    .bss (NOLOAD) : ALIGN(4) {
        __bss_start = .;
        *(.bss*)
        *(COMMON)
        __bss_end = .;
    }
    . = ALIGN(16);
    . += 0x4000;
    __stack_top = .;
    /DISCARD/ : { *(.comment*) *(.note*) }
}
