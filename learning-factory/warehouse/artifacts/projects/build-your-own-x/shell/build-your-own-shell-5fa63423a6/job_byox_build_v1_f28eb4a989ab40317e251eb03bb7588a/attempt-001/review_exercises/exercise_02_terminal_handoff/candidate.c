/* Review excerpt: helper declarations intentionally omit unrelated details. */
#include <signal.h>
#include <stddef.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>

struct pipeline;

pid_t fork_stage(const struct pipeline *pipeline, size_t stage);
int pipeline_stage_count(const struct pipeline *pipeline);
int remember_job(pid_t process_group, const struct pipeline *pipeline);

int launch_foreground(const struct pipeline *pipeline, int terminal_fd)
{
    pid_t process_group = 0;
    int stage_count = pipeline_stage_count(pipeline);
    int stage;
    int status;

    for (stage = 0; stage < stage_count; ++stage) {
        pid_t child = fork_stage(pipeline, (size_t)stage);
        if (child < 0) {
            return -1;
        }
        if (process_group == 0) {
            process_group = child;
            (void)tcsetpgrp(terminal_fd, process_group);
        }
        (void)setpgid(child, process_group);
    }

    if (remember_job(process_group, pipeline) == -1) {
        return -1;
    }

    if (waitpid(process_group, &status, 0) == -1) {
        return -1;
    }

    if (tcsetpgrp(terminal_fd, getpgrp()) == -1) {
        return -1;
    }
    return status;
}

