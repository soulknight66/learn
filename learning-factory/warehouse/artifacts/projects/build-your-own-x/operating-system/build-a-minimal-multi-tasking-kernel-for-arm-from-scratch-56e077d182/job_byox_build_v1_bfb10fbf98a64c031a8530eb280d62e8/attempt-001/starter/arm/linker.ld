ENTRY(_start)

SECTIONS {
    . = 0x40010000;
    .text : { KEEP(*(.text.boot)) *(.text*) }
    .rodata : { *(.rodata*) }
    .data : { *(.data*) }
    .bss (NOLOAD) : {
        __bss_start = .;
        *(.bss*) *(COMMON)
        __bss_end = .;
    }
    . = ALIGN(16);
    . += 0x4000;
    __stack_top = .;
}
