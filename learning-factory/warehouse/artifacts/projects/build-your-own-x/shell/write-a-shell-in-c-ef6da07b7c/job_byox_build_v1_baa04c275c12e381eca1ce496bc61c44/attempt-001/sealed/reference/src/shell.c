#include "msh.h"

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

typedef struct {
    msh_job_table jobs;
    int interactive;
    pid_t shell_pgid;
    int last_status;
    int exit_requested;
    int exit_status;
} shell_state;

static int normalize_status(int status)
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
    return 1;
}

static int set_signal_disposition(int signal_number, void (*handler)(int))
{
    struct sigaction action;

    memset(&action, 0, sizeof(action));
    action.sa_handler = handler;
    (void)sigemptyset(&action.sa_mask);
    return sigaction(signal_number, &action, NULL);
}

static void reset_child_signals(void)
{
    (void)set_signal_disposition(SIGINT, SIG_DFL);
    (void)set_signal_disposition(SIGQUIT, SIG_DFL);
    (void)set_signal_disposition(SIGTSTP, SIG_DFL);
    (void)set_signal_disposition(SIGTTIN, SIG_DFL);
    (void)set_signal_disposition(SIGTTOU, SIG_DFL);
}

static int set_terminal_group(pid_t pgid)
{
    int result;

    do {
        result = tcsetpgrp(STDIN_FILENO, pgid);
    } while (result < 0 && errno == EINTR);
    return result;
}

static int initialize_shell(shell_state *shell)
{
    memset(shell, 0, sizeof(*shell));
    msh_jobs_init(&shell->jobs);
    shell->interactive = isatty(STDIN_FILENO);
    shell->shell_pgid = getpgrp();

    if (!shell->interactive) {
        return 0;
    }

    while (tcgetpgrp(STDIN_FILENO) != getpgrp()) {
        if (kill(-getpgrp(), SIGTTIN) < 0 && errno != EINTR) {
            (void)fprintf(stderr, "msh: cannot acquire terminal: %s\n", strerror(errno));
            return -1;
        }
    }

    shell->shell_pgid = getpid();
    if (setpgid(0, shell->shell_pgid) < 0 && errno != EACCES && errno != EPERM) {
        (void)fprintf(stderr, "msh: setpgid: %s\n", strerror(errno));
        return -1;
    }
    shell->shell_pgid = getpgrp();
    if (set_signal_disposition(SIGINT, SIG_IGN) < 0 ||
        set_signal_disposition(SIGQUIT, SIG_IGN) < 0 ||
        set_signal_disposition(SIGTSTP, SIG_IGN) < 0 ||
        set_signal_disposition(SIGTTIN, SIG_IGN) < 0 ||
        set_signal_disposition(SIGTTOU, SIG_IGN) < 0 ||
        set_terminal_group(shell->shell_pgid) < 0) {
        (void)fprintf(stderr, "msh: interactive setup failed: %s\n", strerror(errno));
        return -1;
    }
    return 0;
}

static int make_cloexec_pipe(int descriptors[2])
{
    if (pipe(descriptors) < 0) {
        return -1;
    }
    if (fcntl(descriptors[0], F_SETFD, FD_CLOEXEC) < 0 ||
        fcntl(descriptors[1], F_SETFD, FD_CLOEXEC) < 0) {
        const int saved = errno;
        (void)close(descriptors[0]);
        (void)close(descriptors[1]);
        errno = saved;
        return -1;
    }
    return 0;
}

static void close_pipes(int (*pipes)[2], size_t count)
{
    size_t index;

    for (index = 0; index < count; ++index) {
        if (pipes[index][0] >= 0) {
            (void)close(pipes[index][0]);
            pipes[index][0] = -1;
        }
        if (pipes[index][1] >= 0) {
            (void)close(pipes[index][1]);
            pipes[index][1] = -1;
        }
    }
}

static void terminate_started_pipeline(pid_t pgid, const pid_t *pids, size_t count)
{
    size_t index;

    if (pgid > 0) {
        (void)kill(-pgid, SIGTERM);
        (void)kill(-pgid, SIGCONT);
    }
    for (index = 0; index < count; ++index) {
        while (waitpid(pids[index], NULL, 0) < 0 && errno == EINTR) {
        }
    }
}

static char *job_text_from_line(const char *line, int background)
{
    const char *start = line;
    const char *end = line + strlen(line);
    size_t length;
    char *text;

    while (*start != '\0' && isspace((unsigned char)*start)) {
        ++start;
    }
    while (end > start && isspace((unsigned char)end[-1])) {
        --end;
    }
    if (background && end > start && end[-1] == '&') {
        --end;
        while (end > start && isspace((unsigned char)end[-1])) {
            --end;
        }
    }
    length = (size_t)(end - start);
    text = malloc(length + 1);
    if (text == NULL) {
        return NULL;
    }
    memcpy(text, start, length);
    text[length] = '\0';
    return text;
}

static int wait_for_foreground(shell_state *shell, pid_t pgid,
                               const pid_t *pids, size_t process_count,
                               const char *job_text)
{
    msh_process_state *states;
    int *statuses;
    size_t unsettled = process_count;
    int result = 1;
    size_t index;
    int saw_stopped = 0;

    states = calloc(process_count, sizeof(*states));
    statuses = calloc(process_count, sizeof(*statuses));
    if (states == NULL || statuses == NULL) {
        (void)fprintf(stderr, "msh: out of memory while waiting for pipeline\n");
        free(states);
        free(statuses);
        terminate_started_pipeline(pgid, pids, process_count);
        return 1;
    }

    while (unsettled > 0) {
        int status;
        pid_t changed = waitpid(-pgid, &status, WUNTRACED);

        if (changed < 0 && errno == EINTR) {
            continue;
        }
        if (changed < 0) {
            if (errno != ECHILD) {
                (void)fprintf(stderr, "msh: waitpid: %s\n", strerror(errno));
            }
            break;
        }
        for (index = 0; index < process_count; ++index) {
            if (pids[index] == changed && states[index] == MSH_PROCESS_RUNNING) {
                statuses[index] = status;
                states[index] = WIFSTOPPED(status) ? MSH_PROCESS_STOPPED : MSH_PROCESS_DONE;
                saw_stopped = saw_stopped || WIFSTOPPED(status);
                --unsettled;
                break;
            }
        }
    }

    if (shell->interactive && set_terminal_group(shell->shell_pgid) < 0) {
        (void)fprintf(stderr, "msh: cannot reclaim terminal: %s\n", strerror(errno));
    }

    if (unsettled > 0) {
        terminate_started_pipeline(pgid, pids, process_count);
    } else if (saw_stopped) {
        const int id = msh_jobs_add(&shell->jobs, pgid, pids, process_count, job_text);

        if (id < 0) {
            (void)fprintf(stderr, "msh: cannot retain stopped job\n");
            terminate_started_pipeline(pgid, pids, process_count);
        } else {
            for (index = 0; index < process_count; ++index) {
                msh_jobs_note_status(&shell->jobs, pids[index], statuses[index]);
            }
            (void)fprintf(stdout, "[%d] Stopped %ld %s\n", id, (long)pgid, job_text);
            (void)fflush(stdout);
            result = normalize_status(statuses[process_count - 1]);
        }
    } else {
        result = normalize_status(statuses[process_count - 1]);
    }

    free(states);
    free(statuses);
    return result;
}

static int launch_pipeline(shell_state *shell, const msh_pipeline *pipeline,
                           const char *line)
{
    const size_t pipe_count = pipeline->count - 1;
    int (*pipes)[2] = NULL;
    pid_t *pids = NULL;
    pid_t pgid = 0;
    size_t created_pipes = 0;
    size_t index;
    char *job_text;
    int result;

    if (pipe_count > SIZE_MAX / sizeof(*pipes) ||
        pipeline->count > SIZE_MAX / sizeof(*pids)) {
        (void)fprintf(stderr, "msh: pipeline is too large\n");
        return 1;
    }
    if (pipe_count > 0) {
        pipes = malloc(pipe_count * sizeof(*pipes));
        if (pipes == NULL) {
            (void)fprintf(stderr, "msh: out of memory for pipes\n");
            return 1;
        }
        for (index = 0; index < pipe_count; ++index) {
            pipes[index][0] = -1;
            pipes[index][1] = -1;
            if (make_cloexec_pipe(pipes[index]) < 0) {
                (void)fprintf(stderr, "msh: pipe: %s\n", strerror(errno));
                close_pipes(pipes, created_pipes);
                free(pipes);
                return 1;
            }
            ++created_pipes;
        }
    }

    pids = calloc(pipeline->count, sizeof(*pids));
    job_text = job_text_from_line(line, pipeline->background);
    if (pids == NULL || job_text == NULL) {
        (void)fprintf(stderr, "msh: out of memory for process state\n");
        close_pipes(pipes, created_pipes);
        free(pipes);
        free(pids);
        free(job_text);
        return 1;
    }

    for (index = 0; index < pipeline->count; ++index) {
        pid_t pid = fork();

        if (pid < 0) {
            (void)fprintf(stderr, "msh: fork: %s\n", strerror(errno));
            close_pipes(pipes, created_pipes);
            terminate_started_pipeline(pgid, pids, index);
            free(pipes);
            free(pids);
            free(job_text);
            return 1;
        }
        if (pid == 0) {
            const pid_t child_group = pgid == 0 ? getpid() : pgid;

            if (setpgid(0, child_group) < 0) {
                (void)fprintf(stderr, "msh: child setpgid: %s\n", strerror(errno));
                _exit(126);
            }
            reset_child_signals();
            if (index > 0 && dup2(pipes[index - 1][0], STDIN_FILENO) < 0) {
                (void)fprintf(stderr, "msh: dup2: %s\n", strerror(errno));
                _exit(126);
            }
            if (index + 1 < pipeline->count &&
                dup2(pipes[index][1], STDOUT_FILENO) < 0) {
                (void)fprintf(stderr, "msh: dup2: %s\n", strerror(errno));
                _exit(126);
            }
            close_pipes(pipes, created_pipes);
            execvp(pipeline->commands[index].argv[0], pipeline->commands[index].argv);
            {
                const int exec_error = errno;
            (void)fprintf(stderr, "msh: %s: %s\n",
                              pipeline->commands[index].argv[0], strerror(exec_error));
                _exit(exec_error == ENOENT ? 127 : 126);
            }
        }

        pids[index] = pid;
        if (pgid == 0) {
            pgid = pid;
        }
        if (setpgid(pid, pgid) < 0 && errno != EACCES && errno != ESRCH) {
            (void)fprintf(stderr, "msh: parent setpgid: %s\n", strerror(errno));
        }
    }
    close_pipes(pipes, created_pipes);
    free(pipes);

    if (pipeline->background) {
        const int id = msh_jobs_add(&shell->jobs, pgid, pids, pipeline->count, job_text);
        if (id < 0) {
            (void)fprintf(stderr, "msh: cannot retain background job\n");
            terminate_started_pipeline(pgid, pids, pipeline->count);
            result = 1;
        } else {
            (void)fprintf(stdout, "[%d] %ld\n", id, (long)pgid);
            (void)fflush(stdout);
            result = 0;
        }
    } else {
        if (shell->interactive && set_terminal_group(pgid) < 0) {
            (void)fprintf(stderr, "msh: cannot give terminal to job: %s\n", strerror(errno));
        }
        result = wait_for_foreground(shell, pgid, pids, pipeline->count, job_text);
    }

    free(job_text);
    free(pids);
    return result;
}

static int is_builtin(const char *name)
{
    return strcmp(name, "cd") == 0 || strcmp(name, "exit") == 0 ||
           strcmp(name, "jobs") == 0 || strcmp(name, "wait") == 0;
}

static int parse_exit_status(const char *text, int *status)
{
    char *end;
    long value;

    errno = 0;
    value = strtol(text, &end, 10);
    if (errno != 0 || *text == '\0' || *end != '\0' || value < 0 || value > 255) {
        return -1;
    }
    *status = (int)value;
    return 0;
}

static int run_builtin(shell_state *shell, const msh_command *command)
{
    const char *name = command->argv[0];

    if (strcmp(name, "cd") == 0) {
        const char *destination;

        if (command->argc > 2) {
            (void)fprintf(stderr, "msh: cd: expected zero or one operand\n");
            return 2;
        }
        destination = command->argc == 2 ? command->argv[1] : getenv("HOME");
        if (destination == NULL) {
            (void)fprintf(stderr, "msh: cd: HOME is not set\n");
            return 1;
        }
        if (chdir(destination) < 0) {
            (void)fprintf(stderr, "msh: cd: %s: %s\n", destination, strerror(errno));
            return 1;
        }
        return 0;
    }

    if (strcmp(name, "exit") == 0) {
        int status = shell->last_status;

        if (command->argc > 2 ||
            (command->argc == 2 && parse_exit_status(command->argv[1], &status) < 0)) {
            (void)fprintf(stderr, "msh: exit: expected one decimal status from 0 to 255\n");
            return 2;
        }
        shell->exit_requested = 1;
        shell->exit_status = status;
        return status;
    }

    if (strcmp(name, "jobs") == 0) {
        if (command->argc != 1) {
            (void)fprintf(stderr, "msh: jobs: no operands accepted\n");
            return 2;
        }
        msh_jobs_print(&shell->jobs, stdout);
        return 0;
    }

    if (command->argc != 1) {
        (void)fprintf(stderr, "msh: wait: no operands accepted\n");
        return 2;
    }
    return msh_jobs_wait_all(&shell->jobs);
}

static int execute_pipeline(shell_state *shell, const msh_pipeline *pipeline,
                            const char *line)
{
    size_t command_index;
    int contains_builtin = 0;

    for (command_index = 0; command_index < pipeline->count; ++command_index) {
        if (is_builtin(pipeline->commands[command_index].argv[0])) {
            contains_builtin = 1;
        }
    }
    if (contains_builtin && (pipeline->count != 1 || pipeline->background)) {
        (void)fprintf(stderr, "msh: built-ins require a standalone foreground command\n");
        return 2;
    }
    if (contains_builtin) {
        return run_builtin(shell, &pipeline->commands[0]);
    }
    return launch_pipeline(shell, pipeline, line);
}

static int process_line(shell_state *shell, const char *line)
{
    msh_pipeline pipeline;
    char error[192];
    msh_parse_result parsed;
    int status;

    parsed = msh_parse_line(line, &pipeline, error, sizeof(error));
    if (parsed == MSH_PARSE_EMPTY) {
        return 0;
    }
    if (parsed == MSH_PARSE_ERROR) {
        (void)fprintf(stderr, "msh: %s\n", error);
        return 2;
    }
    status = execute_pipeline(shell, &pipeline, line);
    msh_pipeline_destroy(&pipeline);
    return status;
}

static int run_command_string(shell_state *shell, const char *command)
{
    shell->last_status = process_line(shell, command);
    return shell->exit_requested ? shell->exit_status : shell->last_status;
}

static int run_stream(shell_state *shell)
{
    char *line = NULL;
    size_t capacity = 0;

    while (!shell->exit_requested) {
        ssize_t length;

        msh_jobs_reap(&shell->jobs);
        if (shell->interactive) {
            (void)fputs("msh$ ", stdout);
            (void)fflush(stdout);
        }
        errno = 0;
        length = getline(&line, &capacity, stdin);
        if (length < 0) {
            if (errno == EINTR) {
                clearerr(stdin);
                continue;
            }
            break;
        }
        shell->last_status = process_line(shell, line);
    }
    free(line);
    return shell->exit_requested ? shell->exit_status : shell->last_status;
}

int main(int argc, char **argv)
{
    shell_state shell;
    int result;

    if (!(argc == 1 || (argc == 3 && strcmp(argv[1], "-c") == 0))) {
        (void)fprintf(stderr, "usage: msh [-c command]\n");
        return 2;
    }
    if (initialize_shell(&shell) < 0) {
        msh_jobs_destroy(&shell.jobs);
        return 1;
    }

    result = argc == 1 ? run_stream(&shell) : run_command_string(&shell, argv[2]);
    msh_jobs_reap(&shell.jobs);
    msh_jobs_destroy(&shell.jobs);
    return result;
}
