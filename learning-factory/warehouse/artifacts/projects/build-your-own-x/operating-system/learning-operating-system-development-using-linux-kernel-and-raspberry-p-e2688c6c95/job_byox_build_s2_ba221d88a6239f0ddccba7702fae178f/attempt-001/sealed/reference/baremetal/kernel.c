#include "minios.h"

#include <stdint.h>

#define UART_BASE ((uintptr_t)0x09000000u)
#define UART_TX_FULL (1u << 5)

static volatile uint32_t *const uart_data =
    (volatile uint32_t *)(UART_BASE + 0x00u);
static volatile uint32_t *const uart_flags =
    (volatile uint32_t *)(UART_BASE + 0x18u);

static void uart_putc(char character)
{
    while ((*uart_flags & UART_TX_FULL) != 0u) {
    }
    *uart_data = (uint32_t)(unsigned char)character;
}

static void uart_puts(const char *text)
{
    while (*text != '\0') {
        if (*text == '\n') {
            uart_putc('\r');
        }
        uart_putc(*text);
        ++text;
    }
}

static void semihost_exit(unsigned long status)
{
    static unsigned long parameters[2];
    register unsigned long operation __asm__("x0") = 0x20u;
    register uintptr_t argument __asm__("x1");

    parameters[0] = 0x20026u;
    parameters[1] = status;
    argument = (uintptr_t)&parameters[0];
    __asm__ volatile("hlt #0xf000"
                     : "+r"(operation)
                     : "r"(argument)
                     : "memory");
    for (;;) {
        __asm__ volatile("wfe");
    }
}

static void fail(const char *stage)
{
    uart_puts("MINIOS: FAIL (");
    uart_puts(stage);
    uart_puts(")\n");
    semihost_exit(1u);
}

static void check_processes(void)
{
    proc_table_t table;
    uint32_t first;
    uint32_t second;
    uint32_t selected;
    int32_t exit_code;

    proc_table_init(&table);
    if (proc_spawn(&table, 0u, (uintptr_t)0x1000u, &first) != OS_OK ||
        proc_spawn(&table, first, (uintptr_t)0x2000u, &second) != OS_OK ||
        proc_schedule(&table, &selected) != OS_OK || selected != first ||
        proc_schedule(&table, &selected) != OS_OK || selected != second ||
        proc_block(&table, second) != OS_OK ||
        proc_schedule(&table, &selected) != OS_OK || selected != first ||
        proc_wake(&table, second) != OS_OK ||
        proc_exit(&table, second, 23) != OS_OK ||
        proc_reap(&table, second, &exit_code) != OS_OK || exit_code != 23) {
        fail("processes");
    }
    uart_puts("processes: ok\n");
}

static void check_virtual_memory(void)
{
    vm_space_t space;
    uint32_t physical;

    vm_space_init(&space);
    if (vm_map(&space, 0x1000u, 0x5000u,
               (uint8_t)(VM_READ | VM_WRITE | VM_USER)) != OS_OK ||
        vm_translate(&space, 0x1234u, VM_WRITE, &physical) != OS_OK ||
        physical != 0x5234u ||
        vm_translate(&space, 0x1234u, VM_EXEC, &physical) != OS_ERR_PERM ||
        vm_unmap(&space, 0x1000u) != OS_OK) {
        fail("virtual-memory");
    }
    uart_puts("virtual-memory: ok\n");
}

static void check_ramfs(void)
{
    static const uint8_t message[] = {'r', 'e', 'a', 'd', 'y'};
    uint8_t result[8];
    ramfs_t fs;
    size_t amount;
    size_t size;
    size_t i;

    fs_init(&fs);
    if (fs_create(&fs, "/boot") != OS_OK ||
        fs_write(&fs, "/boot", 2u, message, sizeof(message), &amount) != OS_OK ||
        amount != sizeof(message) ||
        fs_stat(&fs, "/boot", &size) != OS_OK || size != 7u ||
        fs_read(&fs, "/boot", 0u, result, sizeof(result), &amount) != OS_OK ||
        amount != 7u || result[0] != 0u || result[1] != 0u) {
        fail("ramfs");
    }
    for (i = 0; i < sizeof(message); ++i) {
        if (result[i + 2u] != message[i]) {
            fail("ramfs-data");
        }
    }
    uart_puts("ramfs: ok\n");
}

void kernel_main(void)
{
    uart_puts("MiniOS freestanding boot\n");
    check_processes();
    check_virtual_memory();
    check_ramfs();
    uart_puts("MINIOS: PASS\n");
    semihost_exit(0u);
}
