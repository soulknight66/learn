#include "invariant_checks.h"

#include <stdio.h>

int main(void)
{
    tk_frame_allocator_t frames;
    tk_scheduler_t scheduler;
    tk_address_space_t space;
    tk_fs_t fs;

    tk_frames_init(&frames, 8u);
    tk_scheduler_init(&scheduler);
    tk_vm_init(&space, &frames);
    tk_fs_init(&fs);
    if (tk_audit_frames(&frames) != 0 || tk_audit_scheduler(&scheduler) != 0 ||
        tk_audit_vm(&space) != 0 || tk_audit_fs(&fs) != 0) {
        return 1;
    }
    if (tk_process_spawn(&scheduler) != 1 || tk_schedule(&scheduler) != 1 ||
        tk_vm_map(&space, 0x1000u, TK_VM_READ | TK_VM_WRITE) != 0 ||
        tk_fs_create(&fs, "audit") != 0) {
        return 1;
    }
    if (tk_audit_scheduler(&scheduler) != 0 || tk_audit_vm(&space) != 0 ||
        tk_audit_fs(&fs) != 0) {
        return 1;
    }
    ++frames.free_count;
    if (tk_audit_frames(&frames) == 0 || tk_audit_vm(&space) == 0) {
        return 1;
    }
    --frames.free_count;
    fs.files[0].name[0] = '\0';
    if (tk_audit_fs(&fs) == 0) {
        return 1;
    }
    puts("production audit prototype: PASS");
    return 0;
}
