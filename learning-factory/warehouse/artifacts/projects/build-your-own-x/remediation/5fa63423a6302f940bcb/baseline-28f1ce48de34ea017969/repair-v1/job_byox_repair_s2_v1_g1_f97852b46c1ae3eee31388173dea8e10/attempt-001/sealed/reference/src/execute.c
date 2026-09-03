#include "minish.h"

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

static void close_once(int descriptor)
{
    if (descriptor >= 0) {
        /* The descriptor state after EINTR is platform-dependent; do not retry. */
        (void)close(descriptor);
    }
}

static void restore_child_signals(void)
{
    const int signals[] = {SIGINT, SIGQUIT, SIGTSTP, SIGTTIN, SIGTTOU};
    struct sigaction action = {.sa_handler = SIG_DFL};
    size_t i;

    (void)sigemptyset(&action.sa_mask);
    action.sa_flags = 0;
    for (i = 0; i < sizeof(signals) / sizeof(signals[0]); ++i) {
        (void)sigaction(signals[i], &action, NULL);
    }
}

static void child_failure(const char *operation, int exit_code)
{
    const int saved_errno = errno;

    errno = saved_errno;
    perror(operation);
    _exit(exit_code);
}

static void move_descriptor(int descriptor, int target, const char *operation)
{
    if (descriptor < 0 || descriptor == target) {
        return;
    }
    if (dup2(descriptor, target) < 0) {
        child_failure(operation, 126);
    }
    close_once(descriptor);
}

static void apply_redirections(const Command *command)
{
    int descriptor;

    if (command->input_path != NULL) {
        descriptor = open(command->input_path, O_RDONLY);
        if (descriptor < 0) {
            child_failure(command->input_path, 126);
        }
        move_descriptor(descriptor, STDIN_FILENO, "dup2 input");
    }
    if (command->output_path != NULL) {
        int flags = O_WRONLY | O_CREAT;

        flags |= command->append_output ? O_APPEND : O_TRUNC;
        descriptor = open(command->output_path, flags, 0666);
        if (descriptor < 0) {
            child_failure(command->output_path, 126);
        }
        move_descriptor(descriptor, STDOUT_FILENO, "dup2 output");
    }
}

static void run_child(const Command *command, int previous_read,
                      const int next_pipe[2], pid_t process_group)
{
    const pid_t target_group = process_group == 0 ? 0 : process_group;

    if (setpgid(0, target_group) < 0) {
        child_failure("setpgid", 126);
    }
    restore_child_signals();

    /* Close the unused read end before it can alias a standard descriptor. */
    close_once(next_pipe[0]);
    move_descriptor(previous_read, STDIN_FILENO, "dup2 pipeline input");
    move_descriptor(next_pipe[1], STDOUT_FILENO, "dup2 pipeline output");

    apply_redirections(command);
    execvp(command->argv[0], command->argv);
    child_failure(command->argv[0], errno == ENOENT ? 127 : 126);
}

static void terminate_partial_job(pid_t process_group, const pid_t *pids,
                                  size_t launched)
{
    size_t i;

    if (process_group > 0) {
        (void)kill(-process_group, SIGKILL);
    }
    for (i = 0; i < launched; ++i) {
        if (pids[i] > 0) {
            (void)kill(pids[i], SIGKILL);
        }
    }
    for (i = 0; i < launched; ++i) {
        int status;

        while (waitpid(pids[i], &status, 0) < 0 && errno == EINTR) {
        }
    }
}

static int decoded_status(int status)
{
    if (WIFEXITED(status)) {
        return WEXITSTATUS(status);
    }
    if (WIFSIGNALED(status)) {
        return 128 + WTERMSIG(status);
    }
    if (WIFSTOPPED(status)) {
        return 128 + WSTOPSIG(status);
    }
    return 125;
}

static int wait_for_foreground(const pid_t *pids, size_t count)
{
    int last_status = 125;
    size_t i;

    for (i = 0; i < count; ++i) {
        int status;
        pid_t waited;

        do {
            waited = waitpid(pids[i], &status, WUNTRACED);
        } while (waited < 0 && errno == EINTR);
        if (waited < 0) {
            perror("waitpid");
            continue;
        }
        if (i + 1 == count) {
            last_status = decoded_status(status);
        }
    }
    return last_status;
}

int execute_pipeline(const Pipeline *pipeline, const ShellContext *context)
{
    pid_t *pids;
    pid_t process_group = 0;
    int previous_read = -1;
    size_t i;
    int result;

    if (pipeline == NULL || pipeline->count == 0 || context == NULL) {
        errno = EINVAL;
        return 125;
    }
    pids = calloc(pipeline->count, sizeof(*pids));
    if (pids == NULL) {
        perror("calloc");
        return 125;
    }

    for (i = 0; i < pipeline->count; ++i) {
        int next_pipe[2] = {-1, -1};
        pid_t child;

        if (i + 1 < pipeline->count && pipe(next_pipe) < 0) {
            perror("pipe");
            close_once(previous_read);
            terminate_partial_job(process_group, pids, i);
            free(pids);
            return 125;
        }
        child = fork();
        if (child == 0) {
            run_child(&pipeline->commands[i], previous_read, next_pipe,
                      process_group);
        }
        if (child < 0) {
            perror("fork");
            close_once(previous_read);
            close_once(next_pipe[0]);
            close_once(next_pipe[1]);
            terminate_partial_job(process_group, pids, i);
            free(pids);
            return 125;
        }
        if (process_group == 0) {
            process_group = child;
        }
        if (setpgid(child, process_group) < 0 && errno != EACCES &&
            errno != ESRCH) {
            perror("setpgid");
            pids[i] = child;
            close_once(previous_read);
            close_once(next_pipe[0]);
            close_once(next_pipe[1]);
            terminate_partial_job(process_group, pids, i + 1);
            free(pids);
            return 125;
        }
        pids[i] = child;
        close_once(previous_read);
        close_once(next_pipe[1]);
        previous_read = next_pipe[0];
    }
    close_once(previous_read);

    if (pipeline->background) {
        (void)fprintf(stderr, "[background %ld]\n", (long)process_group);
        (void)fflush(stderr);
        free(pids);
        return 0;
    }

    if (context->interactive &&
        tcsetpgrp(context->terminal_fd, process_group) < 0) {
        perror("tcsetpgrp job");
    }
    result = wait_for_foreground(pids, pipeline->count);
    if (context->interactive &&
        tcsetpgrp(context->terminal_fd, context->shell_pgid) < 0) {
        perror("tcsetpgrp shell");
    }
    free(pids);
    return result;
}

size_t shell_reap_background(void)
{
    size_t reaped = 0;

    for (;;) {
        int status;
        pid_t child = waitpid(-1, &status, WNOHANG | WUNTRACED | WCONTINUED);

        if (child > 0) {
            if (WIFEXITED(status) || WIFSIGNALED(status)) {
                ++reaped;
            }
            continue;
        }
        if (child < 0 && errno == EINTR) {
            continue;
        }
        break;
    }
    return reaped;
}
