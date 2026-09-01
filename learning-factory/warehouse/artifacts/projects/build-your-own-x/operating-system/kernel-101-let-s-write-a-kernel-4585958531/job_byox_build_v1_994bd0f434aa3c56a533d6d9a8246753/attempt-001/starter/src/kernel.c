#include "tinykernel.h"

void console_write(const char *text);

void kernel_main(uint32_t multiboot_magic, uint32_t multiboot_info)
{
    tk_frame_allocator_t frames;
    tk_scheduler_t scheduler;
    tk_address_space_t space;
    tk_fs_t fs;
    static const uint8_t message[] = {'b', 'o', 'o', 't'};
    int ok = 1;

    (void)multiboot_info;
    if (multiboot_magic != 0x2BADB002u) {
        console_write("TinyKernel: invalid boot protocol\n");
        return;
    }

    tk_frames_init(&frames, 32u);
    tk_scheduler_init(&scheduler);
    tk_vm_init(&space, &frames);
    tk_fs_init(&fs);

    ok = ok && (tk_process_spawn(&scheduler) == 1);
    ok = ok && (tk_schedule(&scheduler) == 1);
    ok = ok && (tk_vm_map(&space, 0x400000u, TK_VM_READ | TK_VM_WRITE) == 0);
    ok = ok && (tk_fs_create(&fs, "boot.log") == 0);
    ok = ok && (tk_fs_write(&fs, "boot.log", message, sizeof(message)) == 0);

    if (ok != 0) {
        console_write("TinyKernel state lab ready\n");
    } else {
        console_write("TinyKernel state lab incomplete\n");
    }
}
