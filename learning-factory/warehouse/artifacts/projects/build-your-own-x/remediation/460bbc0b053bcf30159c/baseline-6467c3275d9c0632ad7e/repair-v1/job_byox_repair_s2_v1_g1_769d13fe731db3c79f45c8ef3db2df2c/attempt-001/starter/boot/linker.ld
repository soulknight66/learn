ENTRY(_start)

PHDRS
{
    text PT_LOAD FLAGS(5);
    data PT_LOAD FLAGS(6);
}

SECTIONS
{
    . = 1M;
    .multiboot : { KEEP(*(.multiboot)) } :text
    .text ALIGN(4096) : { *(.text*) } :text
    .rodata ALIGN(4096) : { *(.rodata*) } :text
    .data ALIGN(4096) : { *(.data*) } :data
    .bss ALIGN(4096) : { *(COMMON) *(.bss*) } :data
}
