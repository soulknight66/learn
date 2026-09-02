#ifndef LF_KERNEL_SCHEDULER_H
#define LF_KERNEL_SCHEDULER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define LF_MAX_TASKS 4u
#define LF_NO_SLOT (-1)

typedef void (*lf_task_entry_t)(void *argument);

typedef enum {
    LF_TASK_UNUSED = 0,
    LF_TASK_READY,
    LF_TASK_RUNNING,
    LF_TASK_BLOCKED,
    LF_TASK_ZOMBIE
} lf_task_state_t;

typedef struct {
    uint32_t pid;
    lf_task_state_t state;
    lf_task_entry_t entry;
    void *argument;
} lf_task_t;

typedef struct {
    lf_task_t tasks[LF_MAX_TASKS];
    int32_t current_slot;
    uint32_t next_pid;
} lf_scheduler_t;

void lf_scheduler_init(lf_scheduler_t *scheduler);
uint32_t lf_scheduler_spawn(lf_scheduler_t *scheduler,
                            lf_task_entry_t entry,
                            void *argument);
uint32_t lf_scheduler_rotate(lf_scheduler_t *scheduler);
uint32_t lf_scheduler_block_current(lf_scheduler_t *scheduler);
uint32_t lf_scheduler_exit_current(lf_scheduler_t *scheduler);
bool lf_scheduler_unblock(lf_scheduler_t *scheduler, uint32_t pid);
bool lf_scheduler_reap(lf_scheduler_t *scheduler, uint32_t pid);
int32_t lf_scheduler_slot_of(const lf_scheduler_t *scheduler, uint32_t pid);
const lf_task_t *lf_scheduler_task(const lf_scheduler_t *scheduler,
                                   uint32_t pid);
bool lf_scheduler_invariant(const lf_scheduler_t *scheduler);

#endif
