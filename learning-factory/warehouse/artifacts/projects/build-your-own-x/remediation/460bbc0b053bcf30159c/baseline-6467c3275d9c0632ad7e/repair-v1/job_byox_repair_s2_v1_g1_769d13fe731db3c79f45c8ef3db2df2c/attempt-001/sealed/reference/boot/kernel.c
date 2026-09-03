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

static int self_check(void)
{
    struct cairn_kernel kernel;
    const char payload[2] = {'O', 'K'};
    char received[2] = {0, 0};
    cairn_size transferred = 99U;
    cairn_u32 physical = 0U;
    int first;
    int second;
    int running;
    int fd;

    cairn_init(&kernel);
    if (cairn_validate(&kernel) != CAIRN_OK ||
        cairn_spawn(&kernel, 0x1000U, &first) != CAIRN_OK || first != 1 ||
        cairn_spawn(&kernel, 0x2000U, &second) != CAIRN_OK || second != 2 ||
        cairn_schedule(&kernel, &running) != CAIRN_OK || running != first ||
        cairn_schedule(&kernel, &running) != CAIRN_OK || running != second ||
        cairn_block_current(&kernel) != CAIRN_OK ||
        cairn_schedule(&kernel, &running) != CAIRN_OK || running != first ||
        cairn_wake(&kernel, second) != CAIRN_OK) {
        return 0;
    }
    if (cairn_map(&kernel, first, 0x4000U, 3U, 0) != CAIRN_OK ||
        cairn_translate(&kernel, first, 0x4007U, 0, &physical) != CAIRN_OK ||
        physical != 0x3007U ||
        cairn_translate(&kernel, first, 0x4007U, 1, &physical) != CAIRN_ERR_PERMISSION) {
        return 0;
    }
    if (cairn_create(&kernel, "boot.log") != CAIRN_OK ||
        cairn_open(&kernel, first, "boot.log", &fd) != CAIRN_OK || fd != 0 ||
        cairn_write(&kernel, first, fd, payload, 2U, &transferred) != CAIRN_OK ||
        transferred != 2U || cairn_seek(&kernel, first, fd, 0U) != CAIRN_OK ||
        cairn_read(&kernel, first, fd, received, 2U, &transferred) != CAIRN_OK ||
        transferred != 2U || received[0] != 'O' || received[1] != 'K' ||
        cairn_unlink(&kernel, "boot.log") != CAIRN_ERR_BUSY ||
        cairn_close(&kernel, first, fd) != CAIRN_OK ||
        cairn_unlink(&kernel, "boot.log") != CAIRN_OK) {
        return 0;
    }
    if (cairn_exit_current(&kernel, 0) != CAIRN_OK ||
        kernel.frame_owner[3] != -1 || cairn_validate(&kernel) != CAIRN_OK) {
        return 0;
    }
    return 1;
}

void kernel_main(cairn_u32 magic, cairn_u32 boot_info)
{
    int passed;

    (void)boot_info;
    serial_init();
    passed = magic == 0x2BADB002U && self_check();
    if (passed) {
        serial_write("CAIRNOS: PASS\n");
        out_byte(0xF4U, 0x10U);
    } else {
        serial_write("CAIRNOS: FAIL\n");
        out_byte(0xF4U, 0x11U);
    }
    for (;;) {
        __asm__ volatile ("cli; hlt");
    }
}
