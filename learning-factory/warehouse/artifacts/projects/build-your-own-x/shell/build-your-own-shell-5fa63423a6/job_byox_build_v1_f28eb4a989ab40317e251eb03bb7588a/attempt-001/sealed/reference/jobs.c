#include "shell.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static volatile sig_atomic_t child_status_changed = 0;
static int sigchld_notification_fd = -1;

static void handle_sigchld(int signal_number) {
    int saved_errno = errno;
    char marker = 'x';

    (void)signal_number;
    child_status_changed = 1;
    if (sigchld_notification_fd >= 0) {
        (void)write(sigchld_notification_fd, &marker, 1U);
    }
    errno = saved_errno;
}

static int set_signal_handler(int signal_number, void (*handler)(int),
                              int flags) {
    struct sigaction action;

    memset(&action, 0, sizeof(action));
    action.sa_handler = handler;
    action.sa_flags = flags;
    if (sigemptyset(&action.sa_mask) < 0) {
        return -1;
    }
    return sigaction(signal_number, &action, NULL);
}

static int ignore_interactive_signals(void) {
    const int signals[] = {SIGINT, SIGQUIT, SIGTSTP, SIGTTIN, SIGTTOU};
    size_t index;

    for (index = 0U; index < sizeof(signals) / sizeof(signals[0]); index++) {
        if (set_signal_handler(signals[index], SIG_IGN, 0) < 0) {
            return -1;
        }
    }
    return 0;
}

static void restore_child_signals(void) {
    const int signals[] = {SIGINT,  SIGQUIT, SIGTSTP, SIGTTIN,
                           SIGTTOU, SIGCHLD, SIGPIPE};
    size_t index;

    for (index = 0U; index < sizeof(signals) / sizeof(signals[0]); index++) {
        (void)set_signal_handler(signals[index], SIG_DFL, 0);
    }
}

static int normalize_internal_fd(int descriptor) {
    int normalized;

    if (descriptor <= STDERR_FILENO) {
        normalized = fcntl(descriptor, F_DUPFD_CLOEXEC, STDERR_FILENO + 1);
        if (normalized < 0) {
            return -1;
        }
        (void)close(descriptor);
        return normalized;
    }
    if (fcntl(descriptor, F_SETFD, FD_CLOEXEC) < 0) {
        return -1;
    }
    return descriptor;
}

static int make_internal_pipe(int descriptors[2]) {
    int raw[2];
    size_t index;

    descriptors[0] = -1;
    descriptors[1] = -1;
    if (pipe(raw) < 0) {
        return -1;
    }
    descriptors[0] = raw[0];
    descriptors[1] = raw[1];
    for (index = 0U; index < 2U; index++) {
        int normalized = normalize_internal_fd(descriptors[index]);
        if (normalized < 0) {
            int saved_errno = errno;
            (void)close(descriptors[0]);
            (void)close(descriptors[1]);
            descriptors[0] = -1;
            descriptors[1] = -1;
            errno = saved_errno;
            return -1;
        }
        descriptors[index] = normalized;
    }
    return 0;
}

static int set_nonblocking(int descriptor) {
    int flags = fcntl(descriptor, F_GETFL);

    if (flags < 0) {
        return -1;
    }
    return fcntl(descriptor, F_SETFL, flags | O_NONBLOCK);
}

static void close_sigchld_pipe(Shell *shell) {
    sigchld_notification_fd = -1;
    if (shell->sigchld_read_fd >= 0) {
        (void)close(shell->sigchld_read_fd);
        shell->sigchld_read_fd = -1;
    }
    if (shell->sigchld_write_fd >= 0) {
        (void)close(shell->sigchld_write_fd);
        shell->sigchld_write_fd = -1;
    }
}

int shell_initialize(Shell *shell) {
    pid_t foreground_group;
    sigset_t sigchld_set;
    int notification_pipe[2];

    memset(shell, 0, sizeof(*shell));
    shell->terminal_fd = STDIN_FILENO;
    shell->next_job_id = 1;
    shell->sigchld_read_fd = -1;
    shell->sigchld_write_fd = -1;
    shell->interactive = isatty(shell->terminal_fd) != 0;

    if (sigemptyset(&sigchld_set) < 0 ||
        sigaddset(&sigchld_set, SIGCHLD) < 0 ||
        sigprocmask(SIG_BLOCK, &sigchld_set,
                    &shell->inherited_signal_mask) < 0) {
        perror("byosh: sigprocmask");
        return -1;
    }
    shell->child_signal_mask = shell->inherited_signal_mask;
    (void)sigdelset(&shell->child_signal_mask, SIGCHLD);
    if (make_internal_pipe(notification_pipe) < 0) {
        perror("byosh: pipe");
        (void)sigprocmask(SIG_SETMASK, &shell->inherited_signal_mask, NULL);
        return -1;
    }
    shell->sigchld_read_fd = notification_pipe[0];
    shell->sigchld_write_fd = notification_pipe[1];
    if (set_nonblocking(shell->sigchld_read_fd) < 0 ||
        set_nonblocking(shell->sigchld_write_fd) < 0) {
        perror("byosh: fcntl");
        close_sigchld_pipe(shell);
        (void)sigprocmask(SIG_SETMASK, &shell->inherited_signal_mask, NULL);
        return -1;
    }
    sigchld_notification_fd = shell->sigchld_write_fd;
    if (set_signal_handler(SIGCHLD, handle_sigchld, 0) < 0) {
        perror("byosh: sigaction");
        close_sigchld_pipe(shell);
        (void)sigprocmask(SIG_SETMASK, &shell->inherited_signal_mask, NULL);
        return -1;
    }
    if (!shell->interactive) {
        shell->shell_pgid = getpgrp();
        return 0;
    }

    for (;;) {
        foreground_group = tcgetpgrp(shell->terminal_fd);
        if (foreground_group < 0) {
            perror("byosh: tcgetpgrp");
            goto initialization_failure;
        }
        if (foreground_group == getpgrp()) {
            break;
        }
        if (kill(-getpgrp(), SIGTTIN) < 0 && errno != EINTR) {
            perror("byosh: SIGTTIN");
            goto initialization_failure;
        }
    }

    if (ignore_interactive_signals() < 0) {
        perror("byosh: sigaction");
        goto initialization_failure;
    }
    shell->shell_pgid = getpid();
    if (setpgid(shell->shell_pgid, shell->shell_pgid) < 0 &&
        errno != EACCES && errno != EPERM) {
        perror("byosh: setpgid");
        goto initialization_failure;
    }
    shell->shell_pgid = getpgrp();
    if (tcsetpgrp(shell->terminal_fd, shell->shell_pgid) < 0) {
        perror("byosh: tcsetpgrp");
        goto initialization_failure;
    }
    if (tcgetattr(shell->terminal_fd, &shell->shell_terminal_modes) < 0) {
        perror("byosh: tcgetattr");
        goto initialization_failure;
    }
    return 0;

initialization_failure:
    close_sigchld_pipe(shell);
    (void)sigprocmask(SIG_SETMASK, &shell->inherited_signal_mask, NULL);
    return -1;
}

static void free_job(Job *job) {
    free(job->command);
    free(job->processes);
    free(job);
}

static void unlink_job(Shell *shell, Job *target) {
    Job **cursor = &shell->jobs;

    while (*cursor != NULL) {
        if (*cursor == target) {
            *cursor = target->next;
            free_job(target);
            return;
        }
        cursor = &(*cursor)->next;
    }
}

void shell_destroy(Shell *shell) {
    Job *job = shell->jobs;

    while (job != NULL) {
        Job *next = job->next;

        if (job->state != JOB_DONE && job->pgid > 0) {
            (void)kill(-job->pgid, SIGHUP);
            if (job->state == JOB_STOPPED) {
                (void)kill(-job->pgid, SIGCONT);
            }
        }
        free_job(job);
        job = next;
    }
    shell->jobs = NULL;
    close_sigchld_pipe(shell);
    (void)sigprocmask(SIG_SETMASK, &shell->inherited_signal_mask, NULL);
}

static Job *find_job_by_pid(Shell *shell, pid_t pid) {
    Job *job;

    for (job = shell->jobs; job != NULL; job = job->next) {
        size_t index;
        for (index = 0U; index < job->process_count; index++) {
            if (job->processes[index].pid == pid) {
                return job;
            }
        }
    }
    return NULL;
}

static void recompute_job_state(Job *job) {
    bool all_completed = true;
    bool all_active_stopped = true;
    bool has_active = false;
    size_t index;

    for (index = 0U; index < job->process_count; index++) {
        const ProcessRecord *process = &job->processes[index];

        if (!process->completed) {
            all_completed = false;
            has_active = true;
            if (!process->stopped) {
                all_active_stopped = false;
            }
        }
    }
    if (all_completed) {
        job->state = JOB_DONE;
    } else if (has_active && all_active_stopped) {
        job->state = JOB_STOPPED;
    } else {
        job->state = JOB_RUNNING;
    }
}

static void record_wait_status(Shell *shell, pid_t pid, int status) {
    Job *job = find_job_by_pid(shell, pid);
    size_t index;

    if (job == NULL) {
        return;
    }
    for (index = 0U; index < job->process_count; index++) {
        ProcessRecord *process = &job->processes[index];
        if (process->pid != pid) {
            continue;
        }
        process->wait_status = status;
        if (WIFSTOPPED(status)) {
            process->stopped = true;
            process->completed = false;
#ifdef WIFCONTINUED
        } else if (WIFCONTINUED(status)) {
            process->stopped = false;
#endif
        } else if (WIFEXITED(status) || WIFSIGNALED(status)) {
            process->completed = true;
            process->stopped = false;
        }
        break;
    }
    recompute_job_state(job);
}

void shell_reap_jobs(Shell *shell, bool notify) {
    char notifications[128];
    int status;
    pid_t pid;
    Job **cursor;

    if (shell->sigchld_read_fd >= 0) {
        for (;;) {
            ssize_t count = read(shell->sigchld_read_fd, notifications,
                                 sizeof(notifications));
            if (count > 0) {
                continue;
            }
            if (count < 0 && errno == EINTR) {
                continue;
            }
            break;
        }
    }
    (void)child_status_changed;
    child_status_changed = 0;
    for (;;) {
        pid = waitpid(-1, &status, WNOHANG | WUNTRACED | WCONTINUED);
        if (pid > 0) {
            record_wait_status(shell, pid, status);
            continue;
        }
        if (pid < 0 && errno == EINTR) {
            continue;
        }
        break;
    }

    cursor = &shell->jobs;
    while (*cursor != NULL) {
        Job *job = *cursor;
        if (job->state == JOB_DONE) {
            if (notify) {
                (void)dprintf(STDERR_FILENO, "[%d] Done %s\n", job->id,
                              job->command);
            }
            *cursor = job->next;
            free_job(job);
        } else {
            cursor = &job->next;
        }
    }
}

static int redirection_fd(RedirectionType type) {
    return type == REDIR_INPUT ? STDIN_FILENO : STDOUT_FILENO;
}

static int apply_redirections(const Command *command) {
    size_t index;

    for (index = 0U; index < command->redirection_count; index++) {
        const Redirection *redirection = &command->redirections[index];
        int flags;
        int descriptor;
        int destination = redirection_fd(redirection->type);

        if (redirection->type == REDIR_INPUT) {
            flags = O_RDONLY;
            descriptor = open(redirection->path, flags);
        } else {
            flags = O_WRONLY | O_CREAT;
            flags |= redirection->type == REDIR_APPEND ? O_APPEND : O_TRUNC;
            descriptor = open(redirection->path, flags, 0666);
        }
        if (descriptor < 0) {
            (void)dprintf(STDERR_FILENO, "byosh: %s: %s\n",
                          redirection->path, strerror(errno));
            return -1;
        }
        if (descriptor != destination && dup2(descriptor, destination) < 0) {
            (void)dprintf(STDERR_FILENO, "byosh: dup2: %s\n",
                          strerror(errno));
            (void)close(descriptor);
            return -1;
        }
        if (descriptor != destination) {
            (void)close(descriptor);
        }
    }
    return 0;
}

typedef struct {
    int target;
    int saved;
    bool was_open;
} SavedDescriptor;

static int save_standard_descriptor(int target, SavedDescriptor *saved) {
    saved->target = target;
    saved->saved = fcntl(target, F_DUPFD_CLOEXEC, STDERR_FILENO + 1);
    if (saved->saved >= 0) {
        saved->was_open = true;
        return 0;
    }
    if (errno == EBADF) {
        saved->was_open = false;
        return 0;
    }
    return -1;
}

static int restore_standard_descriptor(SavedDescriptor *saved) {
    if (saved->was_open) {
        int result = dup2(saved->saved, saved->target);
        int saved_errno = errno;
        (void)close(saved->saved);
        saved->saved = -1;
        errno = saved_errno;
        return result < 0 ? -1 : 0;
    }
    if (close(saved->target) < 0 && errno != EBADF) {
        return -1;
    }
    return 0;
}

static int run_parent_builtin(Shell *shell, const Command *command) {
    SavedDescriptor saved_input;
    SavedDescriptor saved_output;
    int status;
    bool restore_failed = false;

    (void)fflush(NULL);
    if (save_standard_descriptor(STDIN_FILENO, &saved_input) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: save stdin: %s\n",
                      strerror(errno));
        return 1;
    }
    if (save_standard_descriptor(STDOUT_FILENO, &saved_output) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: save stdout: %s\n",
                      strerror(errno));
        if (saved_input.was_open) {
            (void)close(saved_input.saved);
        }
        return 1;
    }
    if (apply_redirections(command) < 0) {
        status = 1;
    } else {
        status = builtin_run(shell, command, true);
    }
    (void)fflush(NULL);
    if (restore_standard_descriptor(&saved_input) < 0) {
        restore_failed = true;
        (void)dprintf(STDERR_FILENO, "byosh: could not restore stdin: %s\n",
                      strerror(errno));
    }
    if (restore_standard_descriptor(&saved_output) < 0) {
        restore_failed = true;
        (void)dprintf(STDERR_FILENO, "byosh: could not restore stdout: %s\n",
                      strerror(errno));
    }
    if (restore_failed) {
        status = 1;
    }
    return status;
}

static int job_result(const Job *job) {
    const ProcessRecord *last;

    if (job->process_count == 0U) {
        return 1;
    }
    last = &job->processes[job->process_count - 1U];
    if (WIFEXITED(last->wait_status)) {
        return WEXITSTATUS(last->wait_status);
    }
    if (WIFSIGNALED(last->wait_status)) {
        return 128 + WTERMSIG(last->wait_status);
    }
    if (WIFSTOPPED(last->wait_status)) {
        return 128 + WSTOPSIG(last->wait_status);
    }
    return 1;
}

static void mark_job_running(Job *job) {
    size_t index;

    for (index = 0U; index < job->process_count; index++) {
        if (!job->processes[index].completed) {
            job->processes[index].stopped = false;
        }
    }
    job->state = JOB_RUNNING;
}

static int give_terminal_to_job(Shell *shell, Job *job,
                                bool restore_job_modes) {
    if (!shell->interactive) {
        return 0;
    }
    if (tcsetpgrp(shell->terminal_fd, job->pgid) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: tcsetpgrp: %s\n",
                      strerror(errno));
        return -1;
    }
    if (restore_job_modes && job->terminal_modes_valid &&
        tcsetattr(shell->terminal_fd, TCSADRAIN, &job->terminal_modes) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: tcsetattr: %s\n",
                      strerror(errno));
        return -1;
    }
    return 0;
}

static void reclaim_terminal(Shell *shell, Job *job) {
    if (!shell->interactive) {
        return;
    }
    if (job != NULL && job->state == JOB_STOPPED &&
        tcgetattr(shell->terminal_fd, &job->terminal_modes) == 0) {
        job->terminal_modes_valid = true;
    }
    if (tcsetpgrp(shell->terminal_fd, shell->shell_pgid) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: tcsetpgrp: %s\n",
                      strerror(errno));
    }
    if (tcsetattr(shell->terminal_fd, TCSADRAIN,
                  &shell->shell_terminal_modes) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: tcsetattr: %s\n",
                      strerror(errno));
    }
}

static int wait_for_foreground_job(Shell *shell, Job *job,
                                   bool continue_stopped,
                                   bool terminal_already_assigned) {
    pid_t pid;
    int status;
    int result;
    sigset_t wait_mask;
    bool mask_changed = false;

    if (!terminal_already_assigned &&
        give_terminal_to_job(shell, job, continue_stopped) < 0 &&
        shell->interactive) {
        reclaim_terminal(shell, job);
        return 1;
    }
    if (continue_stopped) {
        if (kill(-job->pgid, SIGCONT) < 0) {
            (void)dprintf(STDERR_FILENO, "byosh: fg: %s\n",
                          strerror(errno));
            reclaim_terminal(shell, job);
            return 1;
        }
        mark_job_running(job);
    }
    if (sigprocmask(SIG_SETMASK, &shell->child_signal_mask, &wait_mask) == 0) {
        mask_changed = true;
    } else {
        (void)dprintf(STDERR_FILENO, "byosh: sigprocmask: %s\n",
                      strerror(errno));
    }

    while (job->state == JOB_RUNNING) {
        pid = waitpid(-job->pgid, &status, WUNTRACED);
        if (pid > 0) {
            record_wait_status(shell, pid, status);
            continue;
        }
        if (pid < 0 && errno == EINTR) {
            continue;
        }
        if (pid < 0 && errno != ECHILD) {
            (void)dprintf(STDERR_FILENO, "byosh: waitpid: %s\n",
                          strerror(errno));
        }
        break;
    }

    if (mask_changed && sigprocmask(SIG_SETMASK, &wait_mask, NULL) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: sigprocmask: %s\n",
                      strerror(errno));
    }
    reclaim_terminal(shell, job);

    result = job_result(job);
    if (job->state == JOB_STOPPED) {
        job->job_control_visible = true;
        (void)dprintf(STDERR_FILENO, "[%d] Stopped %s\n", job->id,
                      job->command);
    } else if (job->state == JOB_DONE) {
        unlink_job(shell, job);
    }
    shell_reap_jobs(shell, true);
    return result;
}

static void close_pipes(int (*pipes)[2], size_t pipe_count) {
    size_t index;

    for (index = 0U; index < pipe_count; index++) {
        if (pipes[index][0] >= 0) {
            (void)close(pipes[index][0]);
        }
        if (pipes[index][1] >= 0) {
            (void)close(pipes[index][1]);
        }
    }
}

static int wait_for_launch(int descriptor) {
    char ignored[32];

    if (descriptor < 0) {
        return 0;
    }
    for (;;) {
        ssize_t count = read(descriptor, ignored, sizeof(ignored));
        if (count == 0) {
            return 0;
        }
        if (count > 0 || (count < 0 && errno == EINTR)) {
            continue;
        }
        return -1;
    }
}

static Job *create_job(Shell *shell, const Pipeline *pipeline) {
    Job *job = calloc(1U, sizeof(*job));
    Job **tail;

    if (job == NULL) {
        return NULL;
    }
    job->command = strdup(pipeline->source);
    job->processes = calloc(pipeline->command_count,
                            sizeof(*job->processes));
    if (job->command == NULL || job->processes == NULL) {
        free_job(job);
        return NULL;
    }
    job->id = shell->next_job_id++;
    job->process_count = pipeline->command_count;
    job->state = JOB_RUNNING;
    tail = &shell->jobs;
    while (*tail != NULL) {
        tail = &(*tail)->next;
    }
    *tail = job;
    return job;
}

static void child_execute(const Pipeline *pipeline, size_t command_index,
                          int (*pipes)[2], size_t pipe_count, pid_t pgid,
                          int launch_read_fd, int launch_write_fd,
                          Shell *shell) {
    const Command *command = &pipeline->commands[command_index];
    pid_t child_group = pgid == 0 ? getpid() : pgid;
    BuiltinKind builtin;
    int status;

    if (setpgid(0, child_group) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: setpgid: %s\n",
                      strerror(errno));
        _exit(126);
    }
    (void)sigprocmask(SIG_SETMASK, &shell->child_signal_mask, NULL);
    restore_child_signals();
    if (launch_write_fd >= 0) {
        (void)close(launch_write_fd);
    }
    if (wait_for_launch(launch_read_fd) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: launch gate: %s\n",
                      strerror(errno));
        _exit(126);
    }
    if (launch_read_fd >= 0) {
        (void)close(launch_read_fd);
    }
    if (shell->sigchld_read_fd >= 0) {
        (void)close(shell->sigchld_read_fd);
        shell->sigchld_read_fd = -1;
    }
    if (shell->sigchld_write_fd >= 0) {
        (void)close(shell->sigchld_write_fd);
        shell->sigchld_write_fd = -1;
    }

    if (command_index > 0U &&
        dup2(pipes[command_index - 1U][0], STDIN_FILENO) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: dup2: %s\n", strerror(errno));
        _exit(126);
    }
    if (command_index < pipe_count &&
        dup2(pipes[command_index][1], STDOUT_FILENO) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: dup2: %s\n", strerror(errno));
        _exit(126);
    }
    close_pipes(pipes, pipe_count);
    if (apply_redirections(command) < 0) {
        _exit(1);
    }

    builtin = builtin_identify(command);
    if (builtin != BUILTIN_NONE) {
        status = builtin_run(shell, command, false);
        (void)fflush(NULL);
        _exit(status);
    }
    execvp(command->argv[0], command->argv);
    if (errno == ENOENT) {
        (void)dprintf(STDERR_FILENO, "byosh: %s: command not found\n",
                      command->argv[0]);
        _exit(127);
    }
    (void)dprintf(STDERR_FILENO, "byosh: %s: %s\n", command->argv[0],
                  strerror(errno));
    _exit(126);
}

int shell_execute_pipeline(Shell *shell, const Pipeline *pipeline) {
    size_t pipe_count = pipeline->command_count - 1U;
    int(*pipes)[2] = NULL;
    sigset_t block_mask;
    sigset_t old_mask;
    int launch_gate[2] = {-1, -1};
    bool terminal_assigned = false;
    Job *job;
    pid_t pgid = 0;
    size_t index;

    if (pipeline->command_count == 1U && !pipeline->background &&
        builtin_identify(&pipeline->commands[0]) != BUILTIN_NONE) {
        return run_parent_builtin(shell, &pipeline->commands[0]);
    }

    if (pipe_count > 0U) {
        if (pipe_count > SIZE_MAX / sizeof(*pipes)) {
            (void)dprintf(STDERR_FILENO, "byosh: pipeline is too large\n");
            return 1;
        }
        pipes = malloc(pipe_count * sizeof(*pipes));
        if (pipes == NULL) {
            (void)dprintf(STDERR_FILENO, "byosh: out of memory\n");
            return 1;
        }
        for (index = 0U; index < pipe_count; index++) {
            pipes[index][0] = -1;
            pipes[index][1] = -1;
        }
        for (index = 0U; index < pipe_count; index++) {
            if (make_internal_pipe(pipes[index]) < 0) {
                (void)dprintf(STDERR_FILENO, "byosh: pipe: %s\n",
                              strerror(errno));
                close_pipes(pipes, pipe_count);
                free(pipes);
                return 1;
            }
        }
    }
    if (shell->interactive && !pipeline->background &&
        make_internal_pipe(launch_gate) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: launch gate: %s\n",
                      strerror(errno));
        close_pipes(pipes, pipe_count);
        free(pipes);
        return 1;
    }

    (void)sigemptyset(&block_mask);
    (void)sigaddset(&block_mask, SIGCHLD);
    if (sigprocmask(SIG_BLOCK, &block_mask, &old_mask) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: sigprocmask: %s\n",
                      strerror(errno));
        close_pipes(pipes, pipe_count);
        free(pipes);
        (void)close(launch_gate[0]);
        (void)close(launch_gate[1]);
        return 1;
    }
    job = create_job(shell, pipeline);
    if (job == NULL) {
        (void)dprintf(STDERR_FILENO, "byosh: out of memory\n");
        (void)sigprocmask(SIG_SETMASK, &old_mask, NULL);
        close_pipes(pipes, pipe_count);
        free(pipes);
        (void)close(launch_gate[0]);
        (void)close(launch_gate[1]);
        return 1;
    }

    for (index = 0U; index < pipeline->command_count; index++) {
        pid_t pid = fork();
        if (pid == 0) {
            child_execute(pipeline, index, pipes, pipe_count, pgid,
                          launch_gate[0], launch_gate[1], shell);
        }
        if (pid < 0) {
            size_t started;
            (void)dprintf(STDERR_FILENO, "byosh: fork: %s\n",
                          strerror(errno));
            if (pgid > 0) {
                (void)kill(-pgid, SIGKILL);
            }
            for (started = 0U; started < index; started++) {
                if (job->processes[started].pid > 0) {
                    (void)kill(job->processes[started].pid, SIGKILL);
                }
            }
            if (launch_gate[1] >= 0) {
                (void)close(launch_gate[1]);
                launch_gate[1] = -1;
            }
            if (launch_gate[0] >= 0) {
                (void)close(launch_gate[0]);
                launch_gate[0] = -1;
            }
            close_pipes(pipes, pipe_count);
            free(pipes);
            (void)sigprocmask(SIG_SETMASK, &old_mask, NULL);
            for (started = 0U; started < index; started++) {
                pid_t waited;
                do {
                    waited = waitpid(job->processes[started].pid, NULL, 0);
                } while (waited < 0 && errno == EINTR);
            }
            unlink_job(shell, job);
            return 1;
        }
        if (pgid == 0) {
            pgid = pid;
            job->pgid = pgid;
        }
        if (setpgid(pid, pgid) < 0 && errno != EACCES && errno != ESRCH) {
            (void)dprintf(STDERR_FILENO, "byosh: setpgid: %s\n",
                          strerror(errno));
        }
        job->processes[index].pid = pid;
    }

    close_pipes(pipes, pipe_count);
    free(pipes);
    if (launch_gate[0] >= 0) {
        (void)close(launch_gate[0]);
        launch_gate[0] = -1;
    }
    if (launch_gate[1] >= 0) {
        if (give_terminal_to_job(shell, job, false) < 0) {
            size_t child_index;

            if (job->pgid > 0) {
                (void)kill(-job->pgid, SIGKILL);
            }
            for (child_index = 0U; child_index < job->process_count;
                 child_index++) {
                if (job->processes[child_index].pid > 0) {
                    (void)kill(job->processes[child_index].pid, SIGKILL);
                }
            }
            (void)close(launch_gate[1]);
            launch_gate[1] = -1;
            for (child_index = 0U; child_index < job->process_count;
                 child_index++) {
                pid_t waited;
                if (job->processes[child_index].pid <= 0) {
                    continue;
                }
                do {
                    waited = waitpid(job->processes[child_index].pid, NULL, 0);
                } while (waited < 0 && errno == EINTR);
            }
            reclaim_terminal(shell, job);
            unlink_job(shell, job);
            (void)sigprocmask(SIG_SETMASK, &old_mask, NULL);
            return 1;
        }
        terminal_assigned = true;
        (void)close(launch_gate[1]);
        launch_gate[1] = -1;
    }
    (void)sigprocmask(SIG_SETMASK, &old_mask, NULL);

    if (pipeline->background) {
        job->job_control_visible = true;
        (void)dprintf(STDERR_FILENO, "[%d] %ld\n", job->id,
                      (long)job->pgid);
        return 0;
    }
    return wait_for_foreground_job(shell, job, false, terminal_assigned);
}

static Job *resolve_job(Shell *shell, const char *job_spec,
                        const char *builtin_name, bool stopped_only) {
    Job *job;
    Job *current = NULL;
    long requested_id;
    char *end = NULL;
    const char *number = job_spec;

    shell_reap_jobs(shell, true);
    if (job_spec == NULL) {
        for (job = shell->jobs; job != NULL; job = job->next) {
            if (job->job_control_visible && job->state != JOB_DONE &&
                (!stopped_only || job->state == JOB_STOPPED) &&
                (current == NULL || job->id > current->id)) {
                current = job;
            }
        }
        if (current == NULL) {
            (void)dprintf(STDERR_FILENO, "byosh: %s: no current job\n",
                          builtin_name);
        }
        return current;
    }
    if (*number == '%') {
        number++;
    }
    errno = 0;
    requested_id = strtol(number, &end, 10);
    if (errno == ERANGE || end == number || *end != '\0' ||
        requested_id <= 0L) {
        (void)dprintf(STDERR_FILENO, "byosh: %s: invalid job: %s\n",
                      builtin_name, job_spec);
        return NULL;
    }
    for (job = shell->jobs; job != NULL; job = job->next) {
        if (job->job_control_visible && (long)job->id == requested_id &&
            job->state != JOB_DONE) {
            return job;
        }
    }
    (void)dprintf(STDERR_FILENO, "byosh: %s: no such job: %s\n",
                  builtin_name, job_spec);
    return NULL;
}

int shell_builtin_jobs(Shell *shell) {
    Job *job;

    shell_reap_jobs(shell, true);
    if (fcntl(STDOUT_FILENO, F_GETFD) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: jobs: output: %s\n",
                      strerror(errno));
        return 1;
    }
    for (job = shell->jobs; job != NULL; job = job->next) {
        const char *state = job->state == JOB_STOPPED ? "Stopped" : "Running";
        if (!job->job_control_visible) {
            continue;
        }
        if (dprintf(STDOUT_FILENO, "[%d] %s %s\n", job->id, state,
                    job->command) < 0) {
            (void)dprintf(STDERR_FILENO, "byosh: jobs: write: %s\n",
                          strerror(errno));
            return 1;
        }
    }
    return 0;
}

int shell_builtin_fg(Shell *shell, const char *job_spec) {
    Job *job = resolve_job(shell, job_spec, "fg", false);
    bool was_stopped;

    if (job == NULL) {
        return 1;
    }
    was_stopped = job->state == JOB_STOPPED;
    return wait_for_foreground_job(shell, job, was_stopped, false);
}

int shell_builtin_bg(Shell *shell, const char *job_spec) {
    Job *job = resolve_job(shell, job_spec, "bg", job_spec == NULL);

    if (job == NULL) {
        return 1;
    }
    if (job->state != JOB_STOPPED) {
        (void)dprintf(STDERR_FILENO, "byosh: bg: job is not stopped: %d\n",
                      job->id);
        return 1;
    }
    if (kill(-job->pgid, SIGCONT) < 0) {
        (void)dprintf(STDERR_FILENO, "byosh: bg: %s\n",
                      strerror(errno));
        return 1;
    }
    mark_job_running(job);
    (void)dprintf(STDERR_FILENO, "[%d] Running %s\n", job->id,
                  job->command);
    return 0;
}
