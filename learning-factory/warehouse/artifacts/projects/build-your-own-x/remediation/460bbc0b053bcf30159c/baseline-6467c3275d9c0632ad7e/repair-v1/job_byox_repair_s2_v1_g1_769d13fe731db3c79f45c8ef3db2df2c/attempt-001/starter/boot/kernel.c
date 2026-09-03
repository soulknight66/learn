#include "cairn.h"

static void out_byte(unsigned short port, unsigned char value)
{
    __asm__ volatile ("outb %0, %1" : : "a"(value), "Nd"(port));
}

static void serial_init(void)
{
    out_byte(0x3F8U + 1U, 0x00U);
    out_byte(0x3F8U + 3U, 0x80U);
    out_byte(0x3F8U + 0U, 0x03U);
    out_byte(0x3F8U + 1U, 0x00U);
    out_byte(0x3F8U + 3U, 0x03U);
    out_byte(0x3F8U + 2U, 0xC7U);
    out_byte(0x3F8U + 4U, 0x0BU);
}

static void serial_write(const char *text)
{
    while (*text != '\0') {
        out_byte(0x3F8U, (unsigned char)*text);
        ++text;
    }
}

void kernel_main(cairn_u32 magic, cairn_u32 boot_info)
{
    struct cairn_kernel kernel;
    int pid = -1;
    int status;

    (void)boot_info;
    serial_init();
    cairn_init(&kernel);
    status = cairn_spawn(&kernel, 0x1000U, &pid);
    if (magic == 0x2BADB002U && status == CAIRN_OK && pid == 1 &&
        cairn_validate(&kernel) == CAIRN_OK) {
        serial_write("CAIRNOS STARTER: CORE READY\n");
        out_byte(0xF4U, 0x10U);
    } else {
        serial_write("CAIRNOS STARTER: CORE INCOMPLETE\n");
        out_byte(0xF4U, 0x11U);
    }
    for (;;) {
        __asm__ volatile ("cli; hlt");
    }
}
