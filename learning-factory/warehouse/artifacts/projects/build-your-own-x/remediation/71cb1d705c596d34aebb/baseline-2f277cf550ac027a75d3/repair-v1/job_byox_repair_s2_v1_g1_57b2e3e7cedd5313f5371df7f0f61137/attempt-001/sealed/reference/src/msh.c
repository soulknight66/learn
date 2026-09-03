#define _POSIX_C_SOURCE 200809L

#include "msh.h"

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>

enum token_kind {
    TOK_WORD,
    TOK_PIPE,
    TOK_AMP,
    TOK_IN,
    TOK_OUT,
    TOK_APPEND
};

struct token {
    enum token_kind kind;
    char *text;
};

struct tokens {
    struct token *items;
    size_t length;
    size_t capacity;
};

struct buffer {
    char *data;
    size_t length;
    size_t capacity;
    bool started;
};

struct command {
    char **argv;
    size_t argc;
    size_t capacity;
    char *input_path;
    char *output_path;
    bool append;
};

struct pipeline {
    struct command *commands;
    size_t length;
    size_t capacity;
    bool background;
    char *source;
};

enum process_state {
    PROCESS_RUNNING,
    PROCESS_STOPPED,
    PROCESS_DONE
};

struct process_info {
    pid_t pid;
    enum process_state state;
    int wait_status;
};

struct job {
    int id;
    pid_t pgid;
    struct process_info *processes;
    size_t process_count;
    size_t last_process;
    char *command;
    struct job *next;
};

struct shell {
    int last_status;
    bool should_exit;
    int exit_status;
    bool interactive;
    int terminal_fd;
    pid_t shell_pgid;
    int next_job_id;
    struct job *jobs;
};

static void *checked_realloc(void *pointer, size_t size) {
    void *result = realloc(pointer, size);
    if (result == NULL) {
        dprintf(STDERR_FILENO, "msh: out of memory\n");
        exit(1);
    }
    return result;
}

static char *checked_strdup(const char *source) {
    char *result = strdup(source);
    if (result == NULL) {
        dprintf(STDERR_FILENO, "msh: out of memory\n");
        exit(1);
    }
    return result;
}

static void buffer_append(struct buffer *buffer, char byte) {
    if (buffer->length + 1 >= buffer->capacity) {
        size_t next = buffer->capacity == 0 ? 32 : buffer->capacity * 2;
        buffer->data = checked_realloc(buffer->data, next);
        buffer->capacity = next;
    }
    buffer->data[buffer->length++] = byte;
    buffer->data[buffer->length] = '\0';
    buffer->started = true;
}

static void buffer_mark_started(struct buffer *buffer) {
    if (buffer->capacity == 0) {
        buffer->data = checked_realloc(NULL, 1);
        buffer->data[0] = '\0';
        buffer->capacity = 1;
    }
    buffer->started = true;
}

static void tokens_push(struct tokens *tokens, enum token_kind kind, char *text) {
    if (tokens->length == tokens->capacity) {
        size_t next = tokens->capacity == 0 ? 16 : tokens->capacity * 2;
        tokens->items = checked_realloc(tokens->items, next * sizeof(*tokens->items));
        tokens->capacity = next;
    }
    tokens->items[tokens->length++] = (struct token){.kind = kind, .text = text};
}

static void lexer_flush_word(struct tokens *tokens, struct buffer *buffer) {
    if (!buffer->started) {
        return;
    }
    char *word = buffer->data == NULL ? checked_strdup("") : buffer->data;
    tokens_push(tokens, TOK_WORD, word);
    *buffer = (struct buffer){0};
}

static void tokens_free(struct tokens *tokens) {
    for (size_t i = 0; i < tokens->length; ++i) {
        free(tokens->items[i].text);
    }
    free(tokens->items);
    *tokens = (struct tokens){0};
}

static int syntax_error(const char *message) {
    dprintf(STDERR_FILENO, "msh: syntax: %s\n", message);
    return 2;
}

static int lex_line(const char *line, struct tokens *tokens) {
    struct buffer word = {0};
    size_t i = 0;

    while (line[i] != '\0') {
        unsigned char byte = (unsigned char)line[i];
        if (byte == ' ' || byte == '\t') {
            lexer_flush_word(tokens, &word);
            ++i;
            continue;
        }
        if (byte == '\\') {
            if (line[i + 1] == '\0') {
                free(word.data);
                tokens_free(tokens);
                return syntax_error("dangling backslash");
            }
            buffer_append(&word, line[i + 1]);
            i += 2;
            continue;
        }
        if (byte == '\'' || byte == '"') {
            char quote = (char)byte;
            buffer_mark_started(&word);
            ++i;
            while (line[i] != '\0' && line[i] != quote) {
                if (quote == '"' && line[i] == '\\') {
                    if (line[i + 1] == '\0') {
                        free(word.data);
                        tokens_free(tokens);
                        return syntax_error("dangling backslash in double quote");
                    }
                    buffer_append(&word, line[i + 1]);
                    i += 2;
                } else {
                    buffer_append(&word, line[i]);
                    ++i;
                }
            }
            if (line[i] == '\0') {
                free(word.data);
                tokens_free(tokens);
                return syntax_error("unterminated quote");
            }
            ++i;
            continue;
        }
        if (byte == '|' || byte == '&' || byte == '<' || byte == '>') {
            enum token_kind kind;
            lexer_flush_word(tokens, &word);
            if (byte == '|') {
                kind = TOK_PIPE;
            } else if (byte == '&') {
                kind = TOK_AMP;
            } else if (byte == '<') {
                kind = TOK_IN;
            } else if (line[i + 1] == '>') {
                kind = TOK_APPEND;
                ++i;
            } else {
                kind = TOK_OUT;
            }
            tokens_push(tokens, kind, NULL);
            ++i;
            continue;
        }
        buffer_append(&word, (char)byte);
        ++i;
    }
    lexer_flush_word(tokens, &word);
    return 0;
}

static void command_free(struct command *command) {
    for (size_t i = 0; i < command->argc; ++i) {
        free(command->argv[i]);
    }
    free(command->argv);
    free(command->input_path);
    free(command->output_path);
    *command = (struct command){0};
}

static void pipeline_free(struct pipeline *pipeline) {
    for (size_t i = 0; i < pipeline->length; ++i) {
        command_free(&pipeline->commands[i]);
    }
    free(pipeline->commands);
    free(pipeline->source);
    *pipeline = (struct pipeline){0};
}

static void command_add_argument(struct command *command, const char *word) {
    if (command->argc + 1 >= command->capacity) {
        size_t next = command->capacity == 0 ? 8 : command->capacity * 2;
        command->argv = checked_realloc(command->argv, next * sizeof(*command->argv));
        command->capacity = next;
    }
    command->argv[command->argc++] = checked_strdup(word);
    command->argv[command->argc] = NULL;
}

static void pipeline_add_command(struct pipeline *pipeline, struct command *command) {
    if (pipeline->length == pipeline->capacity) {
        size_t next = pipeline->capacity == 0 ? 4 : pipeline->capacity * 2;
        pipeline->commands = checked_realloc(
            pipeline->commands, next * sizeof(*pipeline->commands));
        pipeline->capacity = next;
    }
    pipeline->commands[pipeline->length++] = *command;
    *command = (struct command){0};
}

static int parse_tokens(const struct tokens *tokens, const char *source,
                        struct pipeline *pipeline) {
    struct command command = {0};
    pipeline->source = checked_strdup(source);

    for (size_t i = 0; i < tokens->length; ++i) {
        const struct token *token = &tokens->items[i];
        if (token->kind == TOK_WORD) {
            command_add_argument(&command, token->text);
            continue;
        }
        if (token->kind == TOK_IN || token->kind == TOK_OUT ||
            token->kind == TOK_APPEND) {
            bool input = token->kind == TOK_IN;
            if (i + 1 >= tokens->length || tokens->items[i + 1].kind != TOK_WORD) {
                command_free(&command);
                pipeline_free(pipeline);
                return syntax_error("redirection requires a path");
            }
            if ((input && command.input_path != NULL) ||
                (!input && command.output_path != NULL)) {
                command_free(&command);
                pipeline_free(pipeline);
                return syntax_error("duplicate redirection");
            }
            const char *path = tokens->items[++i].text;
            if (input) {
                command.input_path = checked_strdup(path);
            } else {
                command.output_path = checked_strdup(path);
                command.append = token->kind == TOK_APPEND;
            }
            continue;
        }
        if (token->kind == TOK_PIPE) {
            if (command.argc == 0) {
                command_free(&command);
                pipeline_free(pipeline);
                return syntax_error("empty pipeline stage");
            }
            pipeline_add_command(pipeline, &command);
            continue;
        }
        if (token->kind == TOK_AMP) {
            if (i + 1 != tokens->length) {
                command_free(&command);
                pipeline_free(pipeline);
                return syntax_error("'&' must be final");
            }
            pipeline->background = true;
            continue;
        }
    }

    if (command.argc == 0) {
        command_free(&command);
        pipeline_free(pipeline);
        return syntax_error("missing command");
    }
    pipeline_add_command(pipeline, &command);
    return 0;
}

static bool job_is_done(const struct job *job) {
    for (size_t i = 0; i < job->process_count; ++i) {
        if (job->processes[i].state != PROCESS_DONE) {
            return false;
        }
    }
    return true;
}

static bool job_is_stopped(const struct job *job) {
    bool has_live_process = false;
    for (size_t i = 0; i < job->process_count; ++i) {
        if (job->processes[i].state == PROCESS_RUNNING) {
            return false;
        }
        if (job->processes[i].state == PROCESS_STOPPED) {
            has_live_process = true;
        }
    }
    return has_live_process;
}

static int status_from_wait(int wait_status) {
    if (WIFEXITED(wait_status)) {
        return WEXITSTATUS(wait_status);
    }
    if (WIFSIGNALED(wait_status)) {
        return 128 + WTERMSIG(wait_status);
    }
    if (WIFSTOPPED(wait_status)) {
        return 128 + WSTOPSIG(wait_status);
    }
    return 1;
}

static int job_status(const struct job *job) {
    return status_from_wait(job->processes[job->last_process].wait_status);
}

static void job_free(struct job *job) {
    if (job == NULL) {
        return;
    }
    free(job->processes);
    free(job->command);
    free(job);
}

static void add_job(struct shell *shell, struct job *job) {
    if (job->id == 0) {
        job->id = shell->next_job_id++;
    }
    struct job **position = &shell->jobs;
    while (*position != NULL && (*position)->id < job->id) {
        position = &(*position)->next;
    }
    job->next = *position;
    *position = job;
}

static struct job *detach_job(struct shell *shell, int id) {
    struct job **position = &shell->jobs;
    while (*position != NULL) {
        if ((*position)->id == id) {
            struct job *result = *position;
            *position = result->next;
            result->next = NULL;
            return result;
        }
        position = &(*position)->next;
    }
    return NULL;
}

static struct job *find_job_by_pid(struct shell *shell, pid_t pid,
                                   struct process_info **process) {
    for (struct job *job = shell->jobs; job != NULL; job = job->next) {
        for (size_t i = 0; i < job->process_count; ++i) {
            if (job->processes[i].pid == pid) {
                *process = &job->processes[i];
                return job;
            }
        }
    }
    return NULL;
}

static void update_process(struct process_info *process, int wait_status) {
    process->wait_status = wait_status;
    if (WIFSTOPPED(wait_status)) {
        process->state = PROCESS_STOPPED;
    } else if (WIFCONTINUED(wait_status)) {
        process->state = PROCESS_RUNNING;
    } else if (WIFEXITED(wait_status) || WIFSIGNALED(wait_status)) {
        process->state = PROCESS_DONE;
    }
}

static void reap_jobs(struct shell *shell, bool notify) {
    for (;;) {
        int wait_status = 0;
        pid_t pid = waitpid(-1, &wait_status, WNOHANG | WUNTRACED | WCONTINUED);
        if (pid == 0) {
            break;
        }
        if (pid < 0) {
            if (errno == EINTR) {
                continue;
            }
            break;
        }
        struct process_info *process = NULL;
        (void)find_job_by_pid(shell, pid, &process);
        if (process != NULL) {
            update_process(process, wait_status);
        }
    }

    struct job **position = &shell->jobs;
    while (*position != NULL) {
        struct job *job = *position;
        if (job_is_done(job)) {
            if (notify) {
                dprintf(STDERR_FILENO, "[%d] Done %s\n", job->id, job->command);
            }
            *position = job->next;
            job_free(job);
        } else {
            position = &job->next;
        }
    }
}

static int set_signal_action(int signal_number, void (*handler)(int)) {
    struct sigaction action;
    memset(&action, 0, sizeof(action));
    action.sa_handler = handler;
    sigemptyset(&action.sa_mask);
    action.sa_flags = 0;
    return sigaction(signal_number, &action, NULL);
}

static void child_signal_defaults(void) {
    (void)set_signal_action(SIGINT, SIG_DFL);
    (void)set_signal_action(SIGQUIT, SIG_DFL);
    (void)set_signal_action(SIGTSTP, SIG_DFL);
    (void)set_signal_action(SIGTTIN, SIG_DFL);
    (void)set_signal_action(SIGTTOU, SIG_DFL);
    (void)set_signal_action(SIGCHLD, SIG_DFL);
}

static int initialize_shell(struct shell *shell) {
    shell->last_status = 0;
    shell->terminal_fd = STDIN_FILENO;
    shell->next_job_id = 1;
    if (set_signal_action(SIGCHLD, SIG_DFL) < 0) {
        dprintf(STDERR_FILENO, "msh: sigaction SIGCHLD: %s\n", strerror(errno));
        return 1;
    }
    shell->interactive = isatty(STDIN_FILENO) && isatty(STDERR_FILENO);
    if (!shell->interactive) {
        return 0;
    }

    shell->shell_pgid = getpid();
    while (tcgetpgrp(shell->terminal_fd) != getpgrp()) {
        if (kill(-getpgrp(), SIGTTIN) < 0 && errno != EINTR) {
            dprintf(STDERR_FILENO, "msh: terminal setup: %s\n", strerror(errno));
            return 1;
        }
    }
    if (setpgid(shell->shell_pgid, shell->shell_pgid) < 0 &&
        errno != EACCES && errno != EPERM) {
        dprintf(STDERR_FILENO, "msh: setpgid: %s\n", strerror(errno));
        return 1;
    }
    shell->shell_pgid = getpgrp();
    if (tcsetpgrp(shell->terminal_fd, shell->shell_pgid) < 0) {
        dprintf(STDERR_FILENO, "msh: tcsetpgrp: %s\n", strerror(errno));
        return 1;
    }
    (void)set_signal_action(SIGINT, SIG_IGN);
    (void)set_signal_action(SIGQUIT, SIG_IGN);
    (void)set_signal_action(SIGTSTP, SIG_IGN);
    (void)set_signal_action(SIGTTIN, SIG_IGN);
    (void)set_signal_action(SIGTTOU, SIG_IGN);
    return 0;
}

static bool is_builtin_name(const char *name) {
    return strcmp(name, "cd") == 0 || strcmp(name, "exit") == 0 ||
           strcmp(name, "jobs") == 0 || strcmp(name, "fg") == 0;
}

static int wait_for_foreground(struct shell *shell, struct job *job, bool resume) {
    bool wait_failed = false;
    if (shell->interactive && tcsetpgrp(shell->terminal_fd, job->pgid) < 0) {
        dprintf(STDERR_FILENO, "msh: tcsetpgrp: %s\n", strerror(errno));
    }
    if (resume) {
        for (size_t i = 0; i < job->process_count; ++i) {
            if (job->processes[i].state == PROCESS_STOPPED) {
                job->processes[i].state = PROCESS_RUNNING;
            }
        }
        if (kill(-job->pgid, SIGCONT) < 0) {
            dprintf(STDERR_FILENO, "msh: fg: SIGCONT: %s\n", strerror(errno));
        }
    }

    while (!job_is_done(job) && !job_is_stopped(job)) {
        int wait_status = 0;
        pid_t pid = waitpid(-job->pgid, &wait_status, WUNTRACED);
        if (pid < 0) {
            if (errno == EINTR) {
                continue;
            }
            dprintf(STDERR_FILENO, "msh: waitpid: %s\n", strerror(errno));
            wait_failed = true;
            break;
        }
        for (size_t i = 0; i < job->process_count; ++i) {
            if (job->processes[i].pid == pid) {
                update_process(&job->processes[i], wait_status);
                break;
            }
        }
    }

    if (shell->interactive && tcsetpgrp(shell->terminal_fd, shell->shell_pgid) < 0) {
        dprintf(STDERR_FILENO, "msh: tcsetpgrp: %s\n", strerror(errno));
    }

    int result = wait_failed ? 1 : job_status(job);
    if (wait_failed) {
        job_free(job);
        return result;
    }
    if (job_is_stopped(job)) {
        add_job(shell, job);
        dprintf(STDERR_FILENO, "[%d] Stopped %s\n", job->id, job->command);
    } else {
        job_free(job);
    }
    return result;
}

static int builtin_cd(const struct command *command) {
    if (command->argc > 2) {
        dprintf(STDERR_FILENO, "msh: cd: too many operands\n");
        return 1;
    }
    const char *path = command->argc == 2 ? command->argv[1] : getenv("HOME");
    if (path == NULL) {
        dprintf(STDERR_FILENO, "msh: cd: HOME is not set\n");
        return 1;
    }
    if (chdir(path) < 0) {
        dprintf(STDERR_FILENO, "msh: cd: %s: %s\n", path, strerror(errno));
        return 1;
    }
    return 0;
}

static int builtin_exit(struct shell *shell, const struct command *command,
                        bool parent_context) {
    if (command->argc > 2) {
        dprintf(STDERR_FILENO, "msh: exit: too many operands\n");
        return 2;
    }
    int status = shell->last_status;
    if (command->argc == 2) {
        const unsigned char *digit = (const unsigned char *)command->argv[1];
        if (*digit == '\0') {
            dprintf(STDERR_FILENO, "msh: exit: numeric status must be 0..255\n");
            return 2;
        }
        for (; *digit != '\0'; ++digit) {
            if (*digit < '0' || *digit > '9') {
                dprintf(STDERR_FILENO,
                        "msh: exit: numeric status must be 0..255\n");
                return 2;
            }
        }
        char *end = NULL;
        errno = 0;
        long value = strtol(command->argv[1], &end, 10);
        if (errno != 0 || *end != '\0' || value > 255) {
            dprintf(STDERR_FILENO, "msh: exit: numeric status must be 0..255\n");
            return 2;
        }
        status = (int)value;
    }
    if (parent_context) {
        shell->should_exit = true;
        shell->exit_status = status;
    }
    return status;
}

static int builtin_jobs(struct shell *shell, const struct command *command) {
    if (command->argc != 1) {
        dprintf(STDERR_FILENO, "msh: jobs: no operands accepted\n");
        return 1;
    }
    reap_jobs(shell, true);
    for (const struct job *job = shell->jobs; job != NULL; job = job->next) {
        const char *state = job_is_stopped(job) ? "Stopped" : "Running";
        dprintf(STDOUT_FILENO, "[%d] %s %s\n", job->id, state, job->command);
    }
    return 0;
}

static int parse_job_id(const char *text, int *id) {
    if (*text == '%') {
        ++text;
    }
    const unsigned char *digit = (const unsigned char *)text;
    if (*digit == '\0') {
        return 1;
    }
    for (; *digit != '\0'; ++digit) {
        if (*digit < '0' || *digit > '9') {
            return 1;
        }
    }
    char *end = NULL;
    errno = 0;
    long value = strtol(text, &end, 10);
    if (errno != 0 || *text == '\0' || *end != '\0' || value <= 0 ||
        value > INT_MAX) {
        return 1;
    }
    *id = (int)value;
    return 0;
}

static int builtin_fg(struct shell *shell, const struct command *command,
                      bool parent_context) {
    if (!parent_context) {
        dprintf(STDERR_FILENO, "msh: fg: unavailable in a child context\n");
        return 1;
    }
    if (command->argc > 2) {
        dprintf(STDERR_FILENO, "msh: fg: too many operands\n");
        return 1;
    }
    reap_jobs(shell, true);
    int id = 0;
    if (command->argc == 2) {
        if (parse_job_id(command->argv[1], &id) != 0) {
            dprintf(STDERR_FILENO, "msh: fg: invalid job\n");
            return 1;
        }
    } else {
        for (const struct job *job = shell->jobs; job != NULL; job = job->next) {
            id = job->id;
        }
    }
    struct job *job = detach_job(shell, id);
    if (job == NULL) {
        dprintf(STDERR_FILENO, "msh: fg: no such job\n");
        return 1;
    }
    return wait_for_foreground(shell, job, job_is_stopped(job));
}

static int run_builtin(struct shell *shell, const struct command *command,
                       bool parent_context) {
    if (strcmp(command->argv[0], "cd") == 0) {
        return builtin_cd(command);
    }
    if (strcmp(command->argv[0], "exit") == 0) {
        return builtin_exit(shell, command, parent_context);
    }
    if (strcmp(command->argv[0], "jobs") == 0) {
        return builtin_jobs(shell, command);
    }
    return builtin_fg(shell, command, parent_context);
}

static int duplicate_above_standard(int descriptor) {
    int duplicate;
    do {
        duplicate = fcntl(descriptor, F_DUPFD, STDERR_FILENO + 1);
    } while (duplicate < 0 && errno == EINTR);
    return duplicate;
}

static int move_above_standard(int descriptor) {
    if (descriptor > STDERR_FILENO) {
        return descriptor;
    }
    int moved = duplicate_above_standard(descriptor);
    if (moved < 0) {
        int error = errno;
        close(descriptor);
        errno = error;
        return -1;
    }
    close(descriptor);
    return moved;
}

static int open_redirection(const char *path, int flags) {
    int descriptor = open(path, flags, 0666);
    if (descriptor >= 0) {
        descriptor = move_above_standard(descriptor);
    }
    if (descriptor < 0) {
        dprintf(STDERR_FILENO, "msh: %s: %s\n", path, strerror(errno));
    }
    return descriptor;
}

static int run_parent_builtin(struct shell *shell, const struct command *command) {
    int input = -1;
    int output = -1;
    int saved_input = -1;
    int saved_output = -1;
    bool input_was_closed = false;
    bool output_was_closed = false;
    int result = 1;

    if (command->input_path != NULL) {
        input = open_redirection(command->input_path, O_RDONLY);
        if (input < 0) {
            goto cleanup;
        }
    }
    if (command->output_path != NULL) {
        int flags = O_WRONLY | O_CREAT | (command->append ? O_APPEND : O_TRUNC);
        output = open_redirection(command->output_path, flags);
        if (output < 0) {
            goto cleanup;
        }
    }
    fflush(NULL);
    if (input >= 0) {
        saved_input = duplicate_above_standard(STDIN_FILENO);
        if (saved_input < 0 && errno == EBADF) {
            input_was_closed = true;
        } else if (saved_input < 0) {
            dprintf(STDERR_FILENO, "msh: save stdin: %s\n", strerror(errno));
            goto cleanup;
        }
        if (dup2(input, STDIN_FILENO) < 0) {
            dprintf(STDERR_FILENO, "msh: redirect stdin: %s\n", strerror(errno));
            goto cleanup;
        }
    }
    if (output >= 0) {
        saved_output = duplicate_above_standard(STDOUT_FILENO);
        if (saved_output < 0 && errno == EBADF) {
            output_was_closed = true;
        } else if (saved_output < 0) {
            dprintf(STDERR_FILENO, "msh: save stdout: %s\n", strerror(errno));
            goto cleanup;
        }
        if (dup2(output, STDOUT_FILENO) < 0) {
            dprintf(STDERR_FILENO, "msh: redirect stdout: %s\n", strerror(errno));
            goto cleanup;
        }
    }
    result = run_builtin(shell, command, true);
    fflush(NULL);

cleanup:
    if (saved_input >= 0) {
        (void)dup2(saved_input, STDIN_FILENO);
    } else if (input_was_closed) {
        close(STDIN_FILENO);
    }
    if (saved_output >= 0) {
        (void)dup2(saved_output, STDOUT_FILENO);
    } else if (output_was_closed) {
        close(STDOUT_FILENO);
    }
    if (input >= 0) {
        close(input);
    }
    if (output >= 0) {
        close(output);
    }
    if (saved_input >= 0) {
        close(saved_input);
    }
    if (saved_output >= 0) {
        close(saved_output);
    }
    return result;
}

static void close_pipes(int *pipes, size_t pipe_count) {
    for (size_t i = 0; i < pipe_count * 2; ++i) {
        if (pipes[i] >= 0) {
            close(pipes[i]);
        }
    }
}

static int create_pipe(int endpoints[2]) {
    int raw[2];
    if (pipe(raw) < 0) {
        return -1;
    }
    endpoints[0] = move_above_standard(raw[0]);
    if (endpoints[0] < 0) {
        int error = errno;
        close(raw[1]);
        errno = error;
        return -1;
    }
    endpoints[1] = move_above_standard(raw[1]);
    if (endpoints[1] < 0) {
        int error = errno;
        close(endpoints[0]);
        endpoints[0] = -1;
        errno = error;
        return -1;
    }
    return 0;
}

static void child_redirect(const struct command *command) {
    if (command->input_path != NULL) {
        int descriptor = open_redirection(command->input_path, O_RDONLY);
        if (descriptor < 0) {
            _exit(1);
        }
        if (dup2(descriptor, STDIN_FILENO) < 0) {
            dprintf(STDERR_FILENO, "msh: dup2: %s\n", strerror(errno));
            _exit(1);
        }
        if (descriptor != STDIN_FILENO) {
            close(descriptor);
        }
    }
    if (command->output_path != NULL) {
        int flags = O_WRONLY | O_CREAT | (command->append ? O_APPEND : O_TRUNC);
        int descriptor = open_redirection(command->output_path, flags);
        if (descriptor < 0) {
            _exit(1);
        }
        if (dup2(descriptor, STDOUT_FILENO) < 0) {
            dprintf(STDERR_FILENO, "msh: dup2: %s\n", strerror(errno));
            _exit(1);
        }
        if (descriptor != STDOUT_FILENO) {
            close(descriptor);
        }
    }
}

static void run_child_stage(struct shell *shell, const struct pipeline *pipeline,
                            size_t index, int *pipes, size_t pipe_count,
                            pid_t pgid) {
    const struct command *command = &pipeline->commands[index];
    if (setpgid(0, pgid == 0 ? 0 : pgid) < 0) {
        dprintf(STDERR_FILENO, "msh: child setpgid: %s\n", strerror(errno));
        _exit(1);
    }
    child_signal_defaults();
    if (index > 0 && dup2(pipes[(index - 1) * 2], STDIN_FILENO) < 0) {
        dprintf(STDERR_FILENO, "msh: dup2: %s\n", strerror(errno));
        _exit(1);
    }
    if (index + 1 < pipeline->length &&
        dup2(pipes[index * 2 + 1], STDOUT_FILENO) < 0) {
        dprintf(STDERR_FILENO, "msh: dup2: %s\n", strerror(errno));
        _exit(1);
    }
    close_pipes(pipes, pipe_count);
    child_redirect(command);
    if (is_builtin_name(command->argv[0])) {
        _exit(run_builtin(shell, command, false));
    }
    execvp(command->argv[0], command->argv);
    int error = errno;
    dprintf(STDERR_FILENO, "msh: %s: %s\n", command->argv[0], strerror(error));
    _exit(error == ENOENT ? 127 : 126);
}

static int execute_pipeline(struct shell *shell, const struct pipeline *pipeline) {
    const struct command *only = &pipeline->commands[0];
    if (pipeline->length == 1 && !pipeline->background &&
        is_builtin_name(only->argv[0])) {
        return run_parent_builtin(shell, only);
    }

    size_t pipe_count = pipeline->length - 1;
    int *pipes = NULL;
    if (pipe_count > 0) {
        pipes = checked_realloc(NULL, pipe_count * 2 * sizeof(*pipes));
        for (size_t i = 0; i < pipe_count * 2; ++i) {
            pipes[i] = -1;
        }
        for (size_t i = 0; i < pipe_count; ++i) {
            if (create_pipe(&pipes[i * 2]) < 0) {
                dprintf(STDERR_FILENO, "msh: pipe: %s\n", strerror(errno));
                close_pipes(pipes, pipe_count);
                free(pipes);
                return 1;
            }
        }
    }

    struct job *job = checked_realloc(NULL, sizeof(*job));
    *job = (struct job){0};
    job->process_count = pipeline->length;
    job->last_process = pipeline->length - 1;
    job->processes = checked_realloc(NULL, pipeline->length * sizeof(*job->processes));
    memset(job->processes, 0, pipeline->length * sizeof(*job->processes));
    job->command = checked_strdup(pipeline->source);

    size_t started = 0;
    for (size_t i = 0; i < pipeline->length; ++i) {
        pid_t pid = fork();
        if (pid == 0) {
            run_child_stage(shell, pipeline, i, pipes, pipe_count, job->pgid);
            _exit(1);
        }
        if (pid < 0) {
            dprintf(STDERR_FILENO, "msh: fork: %s\n", strerror(errno));
            close_pipes(pipes, pipe_count);
            if (job->pgid > 0) {
                (void)kill(-job->pgid, SIGTERM);
            }
            for (size_t j = 0; j < started; ++j) {
                while (waitpid(job->processes[j].pid, NULL, 0) < 0 && errno == EINTR) {
                }
            }
            free(pipes);
            job_free(job);
            return 1;
        }
        if (job->pgid == 0) {
            job->pgid = pid;
        }
        if (setpgid(pid, job->pgid) < 0 && errno != EACCES && errno != ESRCH) {
            dprintf(STDERR_FILENO, "msh: setpgid: %s\n", strerror(errno));
        }
        job->processes[i] = (struct process_info){
            .pid = pid,
            .state = PROCESS_RUNNING,
            .wait_status = 0,
        };
        ++started;
    }
    close_pipes(pipes, pipe_count);
    free(pipes);

    if (pipeline->background) {
        add_job(shell, job);
        dprintf(STDERR_FILENO, "[%d] %ld\n", job->id, (long)job->pgid);
        return 0;
    }
    return wait_for_foreground(shell, job, false);
}

static int execute_line(struct shell *shell, const char *line) {
    struct tokens tokens = {0};
    int status = lex_line(line, &tokens);
    if (status != 0) {
        return status;
    }
    if (tokens.length == 0) {
        tokens_free(&tokens);
        return 0;
    }
    struct pipeline pipeline = {0};
    status = parse_tokens(&tokens, line, &pipeline);
    tokens_free(&tokens);
    if (status != 0) {
        return status;
    }
    status = execute_pipeline(shell, &pipeline);
    pipeline_free(&pipeline);
    return status;
}

static void free_shell_jobs(struct shell *shell) {
    struct job *job = shell->jobs;
    while (job != NULL) {
        struct job *next = job->next;
        job_free(job);
        job = next;
    }
    shell->jobs = NULL;
}

int msh_main(int argc, char **argv) {
    struct shell shell = {0};
    if (initialize_shell(&shell) != 0) {
        return 1;
    }
    if (argc == 3 && strcmp(argv[1], "-c") == 0) {
        int status = execute_line(&shell, argv[2]);
        shell.last_status = status;
        reap_jobs(&shell, false);
        free_shell_jobs(&shell);
        return shell.should_exit ? shell.exit_status : status;
    }
    if (argc != 1) {
        dprintf(STDERR_FILENO, "usage: msh [-c command]\n");
        return 2;
    }

    char *line = NULL;
    size_t capacity = 0;
    while (!shell.should_exit) {
        reap_jobs(&shell, true);
        if (shell.interactive) {
            dprintf(STDERR_FILENO, "msh$ ");
        }
        errno = 0;
        ssize_t length = getline(&line, &capacity, stdin);
        if (length < 0) {
            if (errno == EINTR) {
                clearerr(stdin);
                continue;
            }
            if (ferror(stdin)) {
                dprintf(STDERR_FILENO, "msh: read: %s\n", strerror(errno));
                shell.last_status = 1;
            }
            break;
        }
        if ((size_t)length > 1024U * 1024U) {
            shell.last_status = syntax_error("input line exceeds 1 MiB");
            continue;
        }
        if (length > 0 && line[length - 1] == '\n') {
            line[length - 1] = '\0';
        }
        shell.last_status = execute_line(&shell, line);
    }
    free(line);
    reap_jobs(&shell, false);
    free_shell_jobs(&shell);
    return shell.should_exit ? shell.exit_status : shell.last_status;
}

int main(int argc, char **argv) {
    return msh_main(argc, argv);
}
