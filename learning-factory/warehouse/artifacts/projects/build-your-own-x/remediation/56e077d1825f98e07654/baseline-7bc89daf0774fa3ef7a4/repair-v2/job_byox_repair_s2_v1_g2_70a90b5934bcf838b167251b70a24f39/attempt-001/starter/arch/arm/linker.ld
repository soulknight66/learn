ENTRY(_start)

PHDRS
{
    text PT_LOAD FLAGS(5);
    data PT_LOAD FLAGS(6);
    stack PT_GNU_STACK FLAGS(6);
}

SECTIONS
{
    . = 0x00010000;
    .text : ALIGN(4) { KEEP(*(.text.boot)) *(.text .text.*) } :text
    .rodata : ALIGN(4) { *(.rodata .rodata.*) } :text
    . = ALIGN(4096);
    .data : ALIGN(4) { *(.data .data.*) } :data
    .bss (NOLOAD) : ALIGN(16384)
    {
        __bss_start = .;
        *(.bss .bss.* COMMON)
        __bss_end = ALIGN(4);
        . = __bss_end;
    } :data
    .stack (NOLOAD) : ALIGN(8)
    {
        . += 16K;
        __stack_top = .;
    } :data
    /DISCARD/ : { *(.comment) *(.ARM.attributes) *(.note*) }
}
