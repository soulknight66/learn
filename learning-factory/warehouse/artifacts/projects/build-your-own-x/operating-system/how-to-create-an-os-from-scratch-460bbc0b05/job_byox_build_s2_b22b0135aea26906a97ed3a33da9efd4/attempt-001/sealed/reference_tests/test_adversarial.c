#include <stdio.h>

#include "cairn.h"

#define OPERATION_COUNT 25000U

static unsigned int random_state = 0xC011CAFEU;

static unsigned int next_random(void)
{
    random_state = random_state * 1664525U + 1013904223U;
    return random_state;
}

static int random_pid(const struct cairn_kernel *kernel)
{
    unsigned int bound = (unsigned int)kernel->next_pid + 2U;
    return (int)(next_random() % bound);
}

int main(void)
{
    static const char *const names[] = {
        "f00", "f01", "f02", "f03", "f04", "f05", "f06", "f07",
        "f08", "f09", "f10", "f11", "f12", "f13", "f14", "f15",
        "f16", "f17", "f18", "f19"
    };
    struct cairn_kernel kernel;
    unsigned char bytes[17];
    unsigned int operation;
    int bootstrap_pid;

    cairn_init(&kernel);
    if (cairn_spawn(&kernel, 0U, &bootstrap_pid) != CAIRN_OK) {
        puts("adversarial test: bootstrap failed");
        return 1;
    }

    for (operation = 0U; operation < OPERATION_COUNT; ++operation) {
        unsigned int choice = next_random() % 14U;
        int pid = random_pid(&kernel);
        int fd = (int)(next_random() % (CAIRN_MAX_FDS + 2U)) - 1;
        const char *name = names[next_random() % (sizeof(names) / sizeof(names[0]))];
        cairn_size transferred = 0xBADU;
        cairn_u32 physical = 0xBAD0BAD0U;
        int output = -1234;
        unsigned int i;

        for (i = 0U; i < sizeof(bytes); ++i) {
            bytes[i] = (unsigned char)next_random();
        }
        switch (choice) {
        case 0U:
            (void)cairn_spawn(&kernel, next_random() % (CAIRN_USER_TOP + 2U), &output);
            break;
        case 1U:
            (void)cairn_schedule(&kernel, &output);
            break;
        case 2U:
            (void)cairn_block_current(&kernel);
            break;
        case 3U:
            (void)cairn_wake(&kernel, pid);
            break;
        case 4U:
            (void)cairn_exit_current(&kernel, (int)next_random());
            break;
        case 5U:
            (void)cairn_map(&kernel, pid,
                            (next_random() % (CAIRN_USER_TOP / CAIRN_PAGE_SIZE + 2U)) *
                                CAIRN_PAGE_SIZE,
                            next_random() % (CAIRN_MAX_FRAMES + 2U),
                            (int)(next_random() % 3U));
            break;
        case 6U:
            (void)cairn_unmap(&kernel, pid,
                              (next_random() % (CAIRN_USER_TOP / CAIRN_PAGE_SIZE + 2U)) *
                                  CAIRN_PAGE_SIZE);
            break;
        case 7U:
            (void)cairn_translate(&kernel, pid, next_random() % (CAIRN_USER_TOP + 2U),
                                  (int)(next_random() % 3U), &physical);
            break;
        case 8U:
            (void)cairn_create(&kernel, name);
            break;
        case 9U:
            (void)cairn_unlink(&kernel, name);
            break;
        case 10U:
            (void)cairn_open(&kernel, pid, name, &output);
            break;
        case 11U:
            (void)cairn_close(&kernel, pid, fd);
            break;
        case 12U:
            if ((next_random() & 1U) == 0U) {
                (void)cairn_seek(&kernel, pid, fd, next_random() % (CAIRN_FILE_CAP + 10U));
            } else {
                (void)cairn_write(&kernel, pid, fd, bytes,
                                  next_random() % (sizeof(bytes) + 1U), &transferred);
            }
            break;
        default:
            (void)cairn_read(&kernel, pid, fd, bytes,
                             next_random() % (sizeof(bytes) + 1U), &transferred);
            break;
        }
        if (cairn_validate(&kernel) != CAIRN_OK) {
            printf("adversarial test: invariant failed after operation %u choice %u\n",
                   operation, choice);
            return 1;
        }
    }
    printf("adversarial test: %u deterministic operations preserved invariants\n",
           OPERATION_COUNT);
    return 0;
}
