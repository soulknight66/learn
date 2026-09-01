#ifndef TINYKERNEL_INVARIANT_CHECKS_H
#define TINYKERNEL_INVARIANT_CHECKS_H

#include "tinykernel.h"

int tk_audit_frames(const tk_frame_allocator_t *frames);
int tk_audit_scheduler(const tk_scheduler_t *scheduler);
int tk_audit_vm(const tk_address_space_t *space);
int tk_audit_fs(const tk_fs_t *fs);

#endif
