#define _POSIX_C_SOURCE 200809L

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

/*
 * minish is intentionally small, but it is a real shell rather than a
 * command-string wrapper.  It lexes and parses a complete command line before
 * starting anything, launches every member of a pipeline in one process
 * group, and keeps enough per-process state to implement jobs, fg, and bg.
 */

typedef enum {
    TOK_WORD,
    TOK_PIPE,
    TOK_SEMI,
    TOK_AMP,
    TOK_IN,
    TOK_OUT,
    TOK_APPEND,
    TOK_END
} TokenKind;

typedef struct {
    TokenKind kind;
    char *text;
    size_t pos;
    size_t end;
} Token;

typedef struct {
    Token *items;
    size_t len;
    size_t cap;
} TokenVec;

typedef enum {
    REDIR_IN,
    REDIR_OUT,
    REDIR_APPEND
} RedirKind;

typedef struct {
    RedirKind kind;
    char *path;
} Redirection;

typedef struct {
    char **argv;
    size_t argc;
    size_t argv_cap;
    Redirection *redirs;
    size_t nredirs;
    size_t redir_cap;
} Command;

typedef struct {
    Command *commands;
    size_t ncommands;
    size_t command_cap;
    bool background;
    char *display;
} Pipeline;

typedef struct {
    Pipeline *pipelines;
    size_t len;
    size_t cap;
} Program;

typedef enum {
    PROC_RUNNING,
    PROC_STOPPED,
    PROC_DONE
} ProcessState;

typedef struct {
    pid_t pid;
    ProcessState state;
    int wait_status;
} ProcessInfo;

typedef enum {
    JOB_RUNNING,
    JOB_STOPPED,
    JOB_DONE
} JobState;

typedef struct {
    int id;
    pid_t pgid;
    ProcessInfo *processes;
    size_t nprocesses;
    char *command;
} Job;

typedef struct {
    Job **jobs;
    size_t njobs;
    size_t job_cap;
    int next_job_id;
    bool interactive;
    bool show_prompt;
    int terminal_fd;
    pid_t shell_pgid;
    struct termios shell_modes;
    int last_status;
    int last_foreground_status;
    bool exiting;
    int exit_status;
} Shell;

static int sigchld_pipe[2] = {-1, -1};

static void sigchld_handler(int signal_number)
{
    int saved_errno = errno;
    char marker = 'x';

    (void)signal_number;
    if (sigchld_pipe[1] >= 0) {
        (void)write(sigchld_pipe[1], &marker, 1);
    }
    errno = saved_errno;
}

static void allocation_failed(void)
{
    fputs("minish: out of memory\n", stderr);
    exit(2);
}

static size_t next_capacity(size_t current, size_t initial,
                            size_t element_size)
{
    size_t result;

    if (current == 0) {
        result = initial;
    } else {
        if (current > SIZE_MAX / 2U) {
            allocation_failed();
        }
        result = current * 2U;
    }
    if (element_size != 0 && result > SIZE_MAX / element_size) {
        allocation_failed();
    }
    return result;
}

static void *xmalloc(size_t size)
{
    void *ptr = malloc(size == 0 ? 1 : size);
    if (ptr == NULL) {
        allocation_failed();
    }
    return ptr;
}

static void *xrealloc(void *old, size_t size)
{
    void *ptr = realloc(old, size == 0 ? 1 : size);
    if (ptr == NULL) {
        allocation_failed();
    }
    return ptr;
}

static void *xmalloc_array(size_t count, size_t element_size)
{
    if (element_size != 0 && count > SIZE_MAX / element_size) {
        allocation_failed();
    }
    return xmalloc(count * element_size);
}

static void *xrealloc_array(void *old, size_t count, size_t element_size)
{
    if (element_size != 0 && count > SIZE_MAX / element_size) {
        allocation_failed();
    }
    return xrealloc(old, count * element_size);
}

static void *xmalloc_terminated(size_t payload_size)
{
    if (payload_size == SIZE_MAX) {
        allocation_failed();
    }
    return xmalloc(payload_size + 1U);
}

static char *xstrdup(const char *text)
{
    char *copy = strdup(text);
    if (copy == NULL) {
        allocation_failed();
    }
    return copy;
}

static int pipe_retry(int descriptors[2])
{
    int result;
    do {
        result = pipe(descriptors);
    } while (result < 0 && errno == EINTR);
    return result;
}

static int fcntl_get_retry(int descriptor, int command)
{
    int result;
    do {
        result = fcntl(descriptor, command);
    } while (result < 0 && errno == EINTR);
    return result;
}

static int fcntl_set_retry(int descriptor, int command, int argument)
{
    int result;
    do {
        result = fcntl(descriptor, command, argument);
    } while (result < 0 && errno == EINTR);
    return result;
}

static int open_retry(const char *path, int flags)
{
    int result;
    do {
        result = open(path, flags);
    } while (result < 0 && errno == EINTR);
    return result;
}

static int open_mode_retry(const char *path, int flags, mode_t mode)
{
    int result;
    do {
        result = open(path, flags, mode);
    } while (result < 0 && errno == EINTR);
    return result;
}

static int dup_retry(int descriptor)
{
    int result;
    do {
        result = dup(descriptor);
    } while (result < 0 && errno == EINTR);
    return result;
}

static int dup2_retry(int old_descriptor, int new_descriptor)
{
    int result;
    do {
        result = dup2(old_descriptor, new_descriptor);
    } while (result < 0 && errno == EINTR);
    return result;
}

static int stat_retry(const char *path, struct stat *metadata)
{
    int result;
    do {
        result = stat(path, metadata);
    } while (result < 0 && errno == EINTR);
    return result;
}

static pid_t tcgetpgrp_retry(int descriptor)
{
    pid_t result;
    do {
        result = tcgetpgrp(descriptor);
    } while (result < 0 && errno == EINTR);
    return result;
}

static int tcgetattr_retry(int descriptor, struct termios *attributes)
{
    int result;
    do {
        result = tcgetattr(descriptor, attributes);
    } while (result < 0 && errno == EINTR);
    return result;
}

static int tcsetattr_retry(int descriptor, int action,
                           const struct termios *attributes)
{
    int result;
    do {
        result = tcsetattr(descriptor, action, attributes);
    } while (result < 0 && errno == EINTR);
    return result;
}

typedef struct {
    char *data;
    size_t len;
    size_t cap;
} StringBuilder;

static void sb_append(StringBuilder *builder, char ch)
{
    if (builder->len == SIZE_MAX) {
        allocation_failed();
    }
    if (builder->len + 1 >= builder->cap) {
        size_t new_cap = next_capacity(builder->cap, 32U, sizeof(*builder->data));
        builder->data = xrealloc_array(builder->data, new_cap,
                                       sizeof(*builder->data));
        builder->cap = new_cap;
    }
    builder->data[builder->len++] = ch;
}

static char *sb_finish(StringBuilder *builder)
{
    sb_append(builder, '\0');
    builder->len--;
    return builder->data;
}

static void token_vec_push(TokenVec *tokens, Token token)
{
    if (tokens->len == tokens->cap) {
        size_t new_cap = next_capacity(tokens->cap, 16U,
                                       sizeof(*tokens->items));
        tokens->items = xrealloc_array(tokens->items, new_cap,
                                       sizeof(*tokens->items));
        tokens->cap = new_cap;
    }
    tokens->items[tokens->len++] = token;
}

static bool is_operator_char(char ch)
{
    return ch == '|' || ch == ';' || ch == '&' || ch == '<' || ch == '>';
}

static int lex_line(const char *line, TokenVec *tokens, char **error)
{
    size_t length = strlen(line);
    size_t i = 0;

    while (i < length) {
        Token token;

        if (isspace((unsigned char)line[i])) {
            i++;
            continue;
        }

        memset(&token, 0, sizeof(token));
        token.pos = i;
        if (is_operator_char(line[i])) {
            char ch = line[i++];
            if (ch == '>') {
                if (i < length && line[i] == '>') {
                    i++;
                    token.kind = TOK_APPEND;
                } else {
                    token.kind = TOK_OUT;
                }
            } else if (ch == '<') {
                token.kind = TOK_IN;
            } else if (ch == '|') {
                token.kind = TOK_PIPE;
            } else if (ch == ';') {
                token.kind = TOK_SEMI;
            } else {
                token.kind = TOK_AMP;
            }
            token.end = i;
            token_vec_push(tokens, token);
            continue;
        }

        {
            StringBuilder word = {0};
            bool started = false;

            while (i < length && !isspace((unsigned char)line[i]) &&
                   !is_operator_char(line[i])) {
                char ch = line[i];
                started = true;
                if (ch == '\\') {
                    i++;
                    if (i == length) {
                        free(word.data);
                        *error = xstrdup("trailing backslash");
                        return -1;
                    }
                    sb_append(&word, line[i++]);
                } else if (ch == '\'') {
                    i++;
                    while (i < length && line[i] != '\'') {
                        sb_append(&word, line[i++]);
                    }
                    if (i == length) {
                        free(word.data);
                        *error = xstrdup("unterminated single quote");
                        return -1;
                    }
                    i++;
                } else if (ch == '"') {
                    i++;
                    while (i < length && line[i] != '"') {
                        if (line[i] == '\\') {
                            i++;
                            if (i == length) {
                                free(word.data);
                                *error = xstrdup("unterminated double quote");
                                return -1;
                            }
                        }
                        sb_append(&word, line[i++]);
                    }
                    if (i == length) {
                        free(word.data);
                        *error = xstrdup("unterminated double quote");
                        return -1;
                    }
                    i++;
                } else {
                    sb_append(&word, line[i++]);
                }
            }

            if (started) {
                token.kind = TOK_WORD;
                token.text = sb_finish(&word);
                token.end = i;
                token_vec_push(tokens, token);
            }
        }
    }

    {
        Token end = {TOK_END, NULL, length, length};
        token_vec_push(tokens, end);
    }
    return 0;
}

static void token_vec_free(TokenVec *tokens)
{
    size_t i;
    for (i = 0; i < tokens->len; i++) {
        free(tokens->items[i].text);
    }
    free(tokens->items);
    memset(tokens, 0, sizeof(*tokens));
}

static void command_add_arg(Command *command, const char *word)
{
    if (command->argv_cap == 0 || command->argc >= command->argv_cap - 1U) {
        size_t new_cap = next_capacity(command->argv_cap, 8U,
                                       sizeof(*command->argv));
        command->argv = xrealloc_array(command->argv, new_cap,
                                       sizeof(*command->argv));
        command->argv_cap = new_cap;
    }
    command->argv[command->argc++] = xstrdup(word);
    command->argv[command->argc] = NULL;
}

static void command_add_redirection(Command *command, RedirKind kind,
                                    const char *path)
{
    if (command->nredirs == command->redir_cap) {
        size_t new_cap = next_capacity(command->redir_cap, 4U,
                                       sizeof(*command->redirs));
        command->redirs = xrealloc_array(command->redirs, new_cap,
                                         sizeof(*command->redirs));
        command->redir_cap = new_cap;
    }
    command->redirs[command->nredirs].kind = kind;
    command->redirs[command->nredirs].path = xstrdup(path);
    command->nredirs++;
}

static void pipeline_add_command(Pipeline *pipeline, Command command)
{
    if (pipeline->ncommands == pipeline->command_cap) {
        size_t new_cap = next_capacity(pipeline->command_cap, 4U,
                                       sizeof(*pipeline->commands));
        pipeline->commands = xrealloc_array(pipeline->commands, new_cap,
                                            sizeof(*pipeline->commands));
        pipeline->command_cap = new_cap;
    }
    pipeline->commands[pipeline->ncommands++] = command;
}

static void program_add_pipeline(Program *program, Pipeline pipeline)
{
    if (program->len == program->cap) {
        size_t new_cap = next_capacity(program->cap, 4U,
                                       sizeof(*program->pipelines));
        program->pipelines = xrealloc_array(program->pipelines, new_cap,
                                            sizeof(*program->pipelines));
        program->cap = new_cap;
    }
    program->pipelines[program->len++] = pipeline;
}

static void command_free(Command *command)
{
    size_t i;
    for (i = 0; i < command->argc; i++) {
        free(command->argv[i]);
    }
    for (i = 0; i < command->nredirs; i++) {
        free(command->redirs[i].path);
    }
    free(command->argv);
    free(command->redirs);
    memset(command, 0, sizeof(*command));
}

static void pipeline_free(Pipeline *pipeline)
{
    size_t i;
    for (i = 0; i < pipeline->ncommands; i++) {
        command_free(&pipeline->commands[i]);
    }
    free(pipeline->commands);
    free(pipeline->display);
    memset(pipeline, 0, sizeof(*pipeline));
}

static void program_free(Program *program)
{
    size_t i;
    for (i = 0; i < program->len; i++) {
        pipeline_free(&program->pipelines[i]);
    }
    free(program->pipelines);
    memset(program, 0, sizeof(*program));
}

static char *trimmed_slice(const char *line, size_t begin, size_t end)
{
    char *copy;
    size_t size;

    while (begin < end && isspace((unsigned char)line[begin])) {
        begin++;
    }
    while (end > begin && isspace((unsigned char)line[end - 1])) {
        end--;
    }
    size = end - begin;
    copy = xmalloc_terminated(size);
    memcpy(copy, line + begin, size);
    copy[size] = '\0';
    return copy;
}

static int parse_command(TokenVec *tokens, size_t *cursor, Command *command,
                         char **error)
{
    bool saw_component = false;

    while (tokens->items[*cursor].kind == TOK_WORD ||
           tokens->items[*cursor].kind == TOK_IN ||
           tokens->items[*cursor].kind == TOK_OUT ||
           tokens->items[*cursor].kind == TOK_APPEND) {
        Token *token = &tokens->items[*cursor];
        saw_component = true;
        if (token->kind == TOK_WORD) {
            command_add_arg(command, token->text);
            (*cursor)++;
        } else {
            RedirKind kind = token->kind == TOK_IN ? REDIR_IN :
                             token->kind == TOK_OUT ? REDIR_OUT : REDIR_APPEND;
            (*cursor)++;
            if (tokens->items[*cursor].kind != TOK_WORD) {
                *error = xstrdup("redirection requires a file name");
                return -1;
            }
            command_add_redirection(command, kind,
                                    tokens->items[*cursor].text);
            (*cursor)++;
        }
    }

    if (!saw_component || command->argc == 0) {
        *error = xstrdup("expected a command");
        return -1;
    }
    return 0;
}

static int parse_program(const char *line, TokenVec *tokens, Program *program,
                         char **error)
{
    size_t cursor = 0;

    while (tokens->items[cursor].kind != TOK_END) {
        Pipeline pipeline;
        size_t pipeline_start = tokens->items[cursor].pos;
        size_t pipeline_end;

        memset(&pipeline, 0, sizeof(pipeline));
        for (;;) {
            Command command;
            memset(&command, 0, sizeof(command));
            if (parse_command(tokens, &cursor, &command, error) < 0) {
                command_free(&command);
                pipeline_free(&pipeline);
                return -1;
            }
            pipeline_add_command(&pipeline, command);
            if (tokens->items[cursor].kind != TOK_PIPE) {
                break;
            }
            cursor++;
            if (tokens->items[cursor].kind == TOK_END ||
                tokens->items[cursor].kind == TOK_PIPE ||
                tokens->items[cursor].kind == TOK_SEMI ||
                tokens->items[cursor].kind == TOK_AMP) {
                *error = xstrdup("expected a command after pipe");
                pipeline_free(&pipeline);
                return -1;
            }
        }

        pipeline_end = tokens->items[cursor].pos;
        pipeline.display = trimmed_slice(line, pipeline_start, pipeline_end);
        if (tokens->items[cursor].kind == TOK_AMP) {
            pipeline.background = true;
            cursor++;
        } else if (tokens->items[cursor].kind == TOK_SEMI) {
            cursor++;
        } else if (tokens->items[cursor].kind != TOK_END) {
            *error = xstrdup("unexpected token");
            pipeline_free(&pipeline);
            return -1;
        }
        program_add_pipeline(program, pipeline);

        if (tokens->items[cursor].kind == TOK_END) {
            break;
        }
        if (tokens->items[cursor].kind == TOK_SEMI ||
            tokens->items[cursor].kind == TOK_AMP ||
            tokens->items[cursor].kind == TOK_PIPE) {
            *error = xstrdup("unexpected operator");
            return -1;
        }
    }
    return 0;
}

static JobState job_state(const Job *job)
{
    size_t i;
    bool any_running = false;
    bool any_stopped = false;

    for (i = 0; i < job->nprocesses; i++) {
        if (job->processes[i].state == PROC_RUNNING) {
            any_running = true;
        } else if (job->processes[i].state == PROC_STOPPED) {
            any_stopped = true;
        }
    }
    if (any_running) {
        return JOB_RUNNING;
    }
    if (any_stopped) {
        return JOB_STOPPED;
    }
    return JOB_DONE;
}

static int decoded_wait_status(int status)
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

static int job_exit_status(const Job *job)
{
    size_t i;

    if (job->nprocesses == 0) {
        return 0;
    }
    if (job_state(job) == JOB_STOPPED) {
        for (i = job->nprocesses; i > 0; i--) {
            if (job->processes[i - 1].state == PROC_STOPPED) {
                return decoded_wait_status(job->processes[i - 1].wait_status);
            }
        }
    }
    return decoded_wait_status(job->processes[job->nprocesses - 1].wait_status);
}

static void job_free(Job *job)
{
    if (job == NULL) {
        return;
    }
    free(job->processes);
    free(job->command);
    free(job);
}

static void shell_add_job(Shell *shell, Job *job)
{
    if (shell->njobs == shell->job_cap) {
        size_t new_cap = next_capacity(shell->job_cap, 8U,
                                       sizeof(*shell->jobs));
        shell->jobs = xrealloc_array(shell->jobs, new_cap,
                                     sizeof(*shell->jobs));
        shell->job_cap = new_cap;
    }
    if (job->id == 0) {
        if (shell->next_job_id == INT_MAX) {
            fputs("minish: job ID space exhausted\n", stderr);
            exit(2);
        }
        job->id = shell->next_job_id++;
    }
    shell->jobs[shell->njobs++] = job;
}

static void shell_remove_job_at(Shell *shell, size_t index)
{
    job_free(shell->jobs[index]);
    if (index + 1 < shell->njobs) {
        memmove(&shell->jobs[index], &shell->jobs[index + 1],
                (shell->njobs - index - 1) * sizeof(*shell->jobs));
    }
    shell->njobs--;
}

static Job *shell_find_job_by_pid(Shell *shell, pid_t pid)
{
    size_t i;
    size_t j;
    for (i = 0; i < shell->njobs; i++) {
        for (j = 0; j < shell->jobs[i]->nprocesses; j++) {
            if (shell->jobs[i]->processes[j].pid == pid) {
                return shell->jobs[i];
            }
        }
    }
    return NULL;
}

static void update_process_status(Job *job, pid_t pid, int status)
{
    size_t i;
    for (i = 0; i < job->nprocesses; i++) {
        ProcessInfo *process = &job->processes[i];
        if (process->pid != pid) {
            continue;
        }
        process->wait_status = status;
        if (WIFSTOPPED(status)) {
            process->state = PROC_STOPPED;
        } else if (WIFCONTINUED(status)) {
            process->state = PROC_RUNNING;
        } else if (WIFEXITED(status) || WIFSIGNALED(status)) {
            process->state = PROC_DONE;
        }
        return;
    }
}

static void refresh_jobs(Shell *shell)
{
    size_t i;

    if (sigchld_pipe[0] >= 0) {
        char buffer[64];
        while (read(sigchld_pipe[0], buffer, sizeof(buffer)) > 0) {
            /* Drain wakeup bytes; waitpid below is the durable event source. */
        }
    }
    for (;;) {
        int status;
        pid_t pid = waitpid(-1, &status, WNOHANG | WUNTRACED | WCONTINUED);
        if (pid > 0) {
            Job *job = shell_find_job_by_pid(shell, pid);
            if (job != NULL) {
                update_process_status(job, pid, status);
            }
            continue;
        }
        if (pid < 0 && errno == EINTR) {
            continue;
        }
        break;
    }

    i = 0;
    while (i < shell->njobs) {
        if (job_state(shell->jobs[i]) == JOB_DONE) {
            shell_remove_job_at(shell, i);
        } else {
            i++;
        }
    }
}

static const char *job_state_name(JobState state)
{
    switch (state) {
    case JOB_RUNNING:
        return "Running";
    case JOB_STOPPED:
        return "Stopped";
    case JOB_DONE:
        return "Done";
    }
    return "Unknown";
}

static int parse_job_id(const char *argument, int *id)
{
    const unsigned char *number;
    unsigned int value = 0U;

    if (argument[0] != '%') {
        return -1;
    }
    number = (const unsigned char *)argument + 1;
    if (*number == '\0') {
        return -1;
    }
    while (*number != '\0') {
        unsigned int digit;
        if (!isdigit(*number)) {
            return -1;
        }
        digit = (unsigned int)(*number - '0');
        if (value > ((unsigned int)INT_MAX - digit) / 10U) {
            return -1;
        }
        value = value * 10U + digit;
        number++;
    }
    if (value == 0U) {
        return -1;
    }
    *id = (int)value;
    return 0;
}

static Job *select_job(Shell *shell, const char *argument, bool stopped_only)
{
    size_t i;

    if (argument != NULL) {
        int id;
        if (parse_job_id(argument, &id) < 0) {
            fprintf(stderr, "minish: invalid job: %s\n", argument);
            return NULL;
        }
        for (i = 0; i < shell->njobs; i++) {
            if (shell->jobs[i]->id == id && job_state(shell->jobs[i]) != JOB_DONE) {
                if (stopped_only && job_state(shell->jobs[i]) != JOB_STOPPED) {
                    fprintf(stderr, "minish: job is not stopped: %s\n", argument);
                    return NULL;
                }
                return shell->jobs[i];
            }
        }
        fprintf(stderr, "minish: no such job: %s\n", argument);
        return NULL;
    }

    for (i = shell->njobs; i > 0; i--) {
        JobState state = job_state(shell->jobs[i - 1]);
        if ((!stopped_only && state != JOB_DONE) ||
            (stopped_only && state == JOB_STOPPED)) {
            return shell->jobs[i - 1];
        }
    }
    fputs(stopped_only ? "minish: no current stopped job\n"
                       : "minish: no current job\n", stderr);
    return NULL;
}

static int apply_redirections(const Command *command)
{
    size_t i;
    for (i = 0; i < command->nredirs; i++) {
        const Redirection *redir = &command->redirs[i];
        int fd;
        int target;

        if (redir->kind == REDIR_IN) {
            fd = open_retry(redir->path, O_RDONLY);
            target = STDIN_FILENO;
        } else if (redir->kind == REDIR_OUT) {
            fd = open_mode_retry(redir->path,
                                 O_WRONLY | O_CREAT | O_TRUNC, 0666);
            target = STDOUT_FILENO;
        } else {
            fd = open_mode_retry(redir->path,
                                 O_WRONLY | O_CREAT | O_APPEND, 0666);
            target = STDOUT_FILENO;
        }
        if (fd < 0) {
            fprintf(stderr, "minish: %s: %s\n", redir->path, strerror(errno));
            return -1;
        }
        if (dup2_retry(fd, target) < 0) {
            fprintf(stderr, "minish: dup2: %s\n", strerror(errno));
            close(fd);
            return -1;
        }
        if (fd != target) {
            close(fd);
        }
    }
    return 0;
}

static void set_signal_action(int signal_number, void (*handler)(int))
{
    struct sigaction action;
    memset(&action, 0, sizeof(action));
    action.sa_handler = handler;
    sigemptyset(&action.sa_mask);
    action.sa_flags = 0;
    if (sigaction(signal_number, &action, NULL) < 0) {
        fprintf(stderr, "minish: sigaction: %s\n", strerror(errno));
        exit(2);
    }
}

static void restore_child_signals(void)
{
    set_signal_action(SIGINT, SIG_DFL);
    set_signal_action(SIGQUIT, SIG_DFL);
    set_signal_action(SIGTSTP, SIG_DFL);
    set_signal_action(SIGTTIN, SIG_DFL);
    set_signal_action(SIGTTOU, SIG_DFL);
    set_signal_action(SIGHUP, SIG_DFL);
    set_signal_action(SIGPIPE, SIG_DFL);
    set_signal_action(SIGCHLD, SIG_DFL);
}

static void mark_job_running(Job *job)
{
    size_t i;
    for (i = 0; i < job->nprocesses; i++) {
        if (job->processes[i].state == PROC_STOPPED) {
            job->processes[i].state = PROC_RUNNING;
        }
    }
}

static int set_terminal_group(Shell *shell, pid_t pgid)
{
    int result;

    do {
        result = tcsetpgrp(shell->terminal_fd, pgid);
    } while (result < 0 && errno == EINTR);
    if (result < 0) {
        fprintf(stderr, "minish: tcsetpgrp: %s\n", strerror(errno));
        return -1;
    }
    return 0;
}

static int put_job_in_foreground(Shell *shell, Job *job, bool continue_job,
                                 bool terminal_already_transferred)
{
    int result;

    if (shell->interactive && !terminal_already_transferred) {
        if (set_terminal_group(shell, job->pgid) < 0) {
            return 1;
        }
    }
    if (continue_job) {
        mark_job_running(job);
        if (kill(-job->pgid, SIGCONT) < 0 && errno != ESRCH) {
            fprintf(stderr, "minish: SIGCONT: %s\n", strerror(errno));
        }
    }

    while (job_state(job) == JOB_RUNNING) {
        int status;
        pid_t pid = waitpid(-job->pgid, &status, WUNTRACED);
        if (pid > 0) {
            update_process_status(job, pid, status);
            continue;
        }
        if (pid < 0 && errno == EINTR) {
            continue;
        }
        if (pid < 0 && errno == ECHILD) {
            size_t i;
            for (i = 0; i < job->nprocesses; i++) {
                if (job->processes[i].state != PROC_DONE) {
                    job->processes[i].state = PROC_DONE;
                    job->processes[i].wait_status = 0;
                }
            }
            break;
        }
        if (pid < 0) {
            fprintf(stderr, "minish: waitpid: %s\n", strerror(errno));
            break;
        }
    }

    if (shell->interactive) {
        (void)set_terminal_group(shell, shell->shell_pgid);
        (void)tcsetattr_retry(shell->terminal_fd, TCSADRAIN,
                              &shell->shell_modes);
    }
    result = job_exit_status(job);
    return result;
}

static int builtin_jobs(Shell *shell, const Command *command)
{
    size_t i;

    if (command->argc != 1) {
        fputs("minish: jobs: no arguments expected\n", stderr);
        return 2;
    }
    refresh_jobs(shell);
    for (i = 0; i < shell->njobs; i++) {
        Job *job = shell->jobs[i];
        JobState state = job_state(job);
        printf("[%d] %-7s %s\n", job->id, job_state_name(state), job->command);
    }
    return 0;
}

static int builtin_fg(Shell *shell, const Command *command, bool parent_context)
{
    Job *job;
    size_t i;
    int result;

    if (!parent_context) {
        fputs("minish: fg: unavailable in a subshell\n", stderr);
        return 1;
    }
    if (command->argc > 2) {
        fputs("minish: fg: expected at most one job\n", stderr);
        return 2;
    }
    refresh_jobs(shell);
    job = select_job(shell, command->argc == 2 ? command->argv[1] : NULL,
                     false);
    if (job == NULL) {
        return 1;
    }
    if (shell->show_prompt) {
        printf("%s\n", job->command);
        fflush(stdout);
    }
    result = put_job_in_foreground(shell, job, job_state(job) == JOB_STOPPED,
                                   false);
    if (job_state(job) == JOB_DONE) {
        for (i = 0; i < shell->njobs; i++) {
            if (shell->jobs[i] == job) {
                shell_remove_job_at(shell, i);
                break;
            }
        }
    }
    return result;
}

static int builtin_bg(Shell *shell, const Command *command, bool parent_context)
{
    Job *job;

    if (!parent_context) {
        fputs("minish: bg: unavailable in a subshell\n", stderr);
        return 1;
    }
    if (command->argc > 2) {
        fputs("minish: bg: expected at most one job\n", stderr);
        return 2;
    }
    refresh_jobs(shell);
    job = select_job(shell, command->argc == 2 ? command->argv[1] : NULL,
                     true);
    if (job == NULL) {
        return 1;
    }
    if (job_state(job) == JOB_STOPPED) {
        mark_job_running(job);
        if (kill(-job->pgid, SIGCONT) < 0) {
            fprintf(stderr, "minish: bg: %s\n", strerror(errno));
            return 1;
        }
    }
    printf("[%d] %s\n", job->id, job->command);
    return 0;
}

static int builtin_cd(const Command *command)
{
    const char *destination;

    if (command->argc > 2) {
        fputs("minish: cd: expected at most one directory\n", stderr);
        return 2;
    }
    if (command->argc == 1) {
        destination = getenv("HOME");
        if (destination == NULL || destination[0] == '\0') {
            fputs("minish: cd: HOME is not set\n", stderr);
            return 1;
        }
    } else {
        destination = command->argv[1];
    }
    if (chdir(destination) < 0) {
        fprintf(stderr, "minish: cd: %s: %s\n", destination, strerror(errno));
        return 1;
    }
    return 0;
}

static int builtin_pwd(const Command *command)
{
    char *directory;

    if (command->argc != 1) {
        fputs("minish: pwd: no arguments expected\n", stderr);
        return 2;
    }
    directory = getcwd(NULL, 0);
    if (directory == NULL) {
        fprintf(stderr, "minish: pwd: %s\n", strerror(errno));
        return 1;
    }
    puts(directory);
    free(directory);
    return 0;
}

static int parse_exit_status(const char *text, int *status)
{
    const unsigned char *cursor = (const unsigned char *)text;
    unsigned int value = 0U;
    bool negative = false;

    if (*cursor == '+' || *cursor == '-') {
        negative = *cursor == '-';
        cursor++;
    }
    if (!isdigit(*cursor)) {
        return -1;
    }
    while (*cursor != '\0' && isdigit(*cursor)) {
        value = (value * 10U + (unsigned int)(*cursor - '0')) % 256U;
        cursor++;
    }
    if (*cursor != '\0') {
        return -1;
    }
    if (negative && value != 0U) {
        value = 256U - value;
    }
    *status = (int)value;
    return 0;
}

static int builtin_exit(Shell *shell, const Command *command, bool parent_context)
{
    int status = shell->last_foreground_status;

    if (command->argc > 2) {
        fputs("minish: exit: expected at most one status\n", stderr);
        return 2;
    }
    if (command->argc == 2 && parse_exit_status(command->argv[1], &status) < 0) {
        fprintf(stderr, "minish: exit: status must be a decimal integer: %s\n",
                command->argv[1]);
        return 2;
    }
    if (parent_context) {
        shell->exiting = true;
        shell->exit_status = status;
    }
    return status;
}

static bool is_builtin(const char *name)
{
    return strcmp(name, "cd") == 0 || strcmp(name, "pwd") == 0 ||
           strcmp(name, "exit") == 0 || strcmp(name, "jobs") == 0 ||
           strcmp(name, "fg") == 0 || strcmp(name, "bg") == 0;
}

static int run_builtin(Shell *shell, const Command *command, bool parent_context)
{
    const char *name = command->argv[0];
    if (strcmp(name, "cd") == 0) {
        return builtin_cd(command);
    }
    if (strcmp(name, "pwd") == 0) {
        return builtin_pwd(command);
    }
    if (strcmp(name, "exit") == 0) {
        return builtin_exit(shell, command, parent_context);
    }
    if (strcmp(name, "jobs") == 0) {
        return builtin_jobs(shell, command);
    }
    if (strcmp(name, "fg") == 0) {
        return builtin_fg(shell, command, parent_context);
    }
    return builtin_bg(shell, command, parent_context);
}

static int run_parent_builtin(Shell *shell, const Command *command)
{
    int saved_stdin = -1;
    int saved_stdout = -1;
    int result = 1;

    fflush(stdout);
    saved_stdin = dup_retry(STDIN_FILENO);
    saved_stdout = dup_retry(STDOUT_FILENO);
    if (saved_stdin < 0 || saved_stdout < 0) {
        fprintf(stderr, "minish: dup: %s\n", strerror(errno));
        goto restore;
    }
    if (apply_redirections(command) < 0) {
        goto restore;
    }
    result = run_builtin(shell, command, true);
    fflush(stdout);

restore:
    if (saved_stdin >= 0) {
        if (dup2_retry(saved_stdin, STDIN_FILENO) < 0) {
            fprintf(stderr, "minish: restore stdin: %s\n", strerror(errno));
            result = 1;
        }
        close(saved_stdin);
    }
    if (saved_stdout >= 0) {
        if (dup2_retry(saved_stdout, STDOUT_FILENO) < 0) {
            fprintf(stderr, "minish: restore stdout: %s\n", strerror(errno));
            result = 1;
        }
        close(saved_stdout);
    }
    return result;
}

static void close_all_pipes(int (*pipes)[2], size_t count)
{
    size_t i;
    for (i = 0; i < count; i++) {
        if (pipes[i][0] >= 0) {
            close(pipes[i][0]);
        }
        if (pipes[i][1] >= 0) {
            close(pipes[i][1]);
        }
    }
}

static bool command_path_exists(const char *name)
{
    const char *path;
    const char *component;
    size_t name_length = strlen(name);

    if (name_length == 0) {
        return false;
    }

    if (strchr(name, '/') != NULL) {
        struct stat metadata;
        return stat_retry(name, &metadata) == 0;
    }

    path = getenv("PATH");
    if (path == NULL) {
        path = "/bin:/usr/bin";
    }
    component = path;
    for (;;) {
        const char *separator = strchr(component, ':');
        size_t directory_length = separator == NULL
                                      ? strlen(component)
                                      : (size_t)(separator - component);
        size_t total;
        char *candidate;
        struct stat metadata;
        bool found;

        if (name_length > SIZE_MAX - 2U ||
            directory_length > SIZE_MAX - name_length - 2U) {
            allocation_failed();
        }
        total = (directory_length == 0 ? 0U : directory_length + 1U) +
                name_length;
        candidate = xmalloc_terminated(total);
        if (directory_length != 0) {
            memcpy(candidate, component, directory_length);
            candidate[directory_length] = '/';
            memcpy(candidate + directory_length + 1U, name, name_length + 1U);
        } else {
            memcpy(candidate, name, name_length + 1U);
        }
        found = stat_retry(candidate, &metadata) == 0;
        free(candidate);
        if (found) {
            return true;
        }
        if (separator == NULL) {
            return false;
        }
        component = separator + 1;
    }
}

static void wait_for_launch_release(int barrier_fd)
{
    char marker;

    for (;;) {
        ssize_t count = read(barrier_fd, &marker, 1);
        if (count == 1) {
            close(barrier_fd);
            if (marker == 'G') {
                return;
            }
            _exit(126);
        }
        if (count < 0 && errno == EINTR) {
            continue;
        }
        if (count == 0) {
            close(barrier_fd);
            _exit(126);
        }
        fprintf(stderr, "minish: launch barrier: %s\n", strerror(errno));
        close(barrier_fd);
        _exit(126);
    }
}

static int release_launch_barrier(int barrier_fd, size_t child_count)
{
    size_t i;

    for (i = 0; i < child_count; i++) {
        ssize_t count;
        do {
            count = write(barrier_fd, "G", 1);
        } while (count < 0 && errno == EINTR);
        if (count != 1) {
            fprintf(stderr, "minish: launch barrier release: %s\n",
                    count < 0 ? strerror(errno) : "short write");
            return -1;
        }
    }
    return 0;
}

static void child_execute(Shell *shell, const Pipeline *pipeline, size_t index,
                          int (*pipes)[2], size_t pipe_count, pid_t pgid,
                          int barrier_read, int barrier_write)
{
    const Command *command = &pipeline->commands[index];
    size_t i;
    int status;
    pid_t target_pgid = pgid == 0 ? getpid() : pgid;

    if (setpgid(0, target_pgid) < 0 && errno != EACCES) {
        fprintf(stderr, "minish: setpgid: %s\n", strerror(errno));
        _exit(126);
    }
    restore_child_signals();
    if (barrier_write >= 0) {
        close(barrier_write);
    }
    if (sigchld_pipe[0] >= 0) {
        close(sigchld_pipe[0]);
        sigchld_pipe[0] = -1;
    }
    if (sigchld_pipe[1] >= 0) {
        close(sigchld_pipe[1]);
        sigchld_pipe[1] = -1;
    }
    if (shell->terminal_fd > STDERR_FILENO) {
        close(shell->terminal_fd);
        shell->terminal_fd = STDIN_FILENO;
    }
    if (barrier_read >= 0) {
        wait_for_launch_release(barrier_read);
    }

    if (index > 0 &&
        dup2_retry(pipes[index - 1][0], STDIN_FILENO) < 0) {
        fprintf(stderr, "minish: pipe input: %s\n", strerror(errno));
        _exit(126);
    }
    if (index < pipe_count &&
        dup2_retry(pipes[index][1], STDOUT_FILENO) < 0) {
        fprintf(stderr, "minish: pipe output: %s\n", strerror(errno));
        _exit(126);
    }
    close_all_pipes(pipes, pipe_count);
    if (pipeline->background && !shell->interactive && index == 0) {
        bool has_input_redirection = false;
        int null_fd;

        for (i = 0; i < command->nredirs; i++) {
            if (command->redirs[i].kind == REDIR_IN) {
                has_input_redirection = true;
                break;
            }
        }
        if (!has_input_redirection) {
            null_fd = open_retry("/dev/null", O_RDONLY);
            if (null_fd < 0) {
                fprintf(stderr, "minish: /dev/null: %s\n", strerror(errno));
                _exit(1);
            }
            if (dup2_retry(null_fd, STDIN_FILENO) < 0) {
                fprintf(stderr, "minish: background stdin: %s\n", strerror(errno));
                if (null_fd != STDIN_FILENO) {
                    close(null_fd);
                }
                _exit(1);
            }
            if (null_fd != STDIN_FILENO) {
                close(null_fd);
            }
        }
    }
    if (apply_redirections(command) < 0) {
        _exit(1);
    }

    if (is_builtin(command->argv[0])) {
        status = run_builtin(shell, command, false);
        fflush(stdout);
        _exit(status);
    }
    do {
        execvp(command->argv[0], command->argv);
    } while (errno == EINTR);
    {
        int saved_errno = errno;
        bool located = command_path_exists(command->argv[0]);
        status = ((saved_errno == ENOENT || saved_errno == ENOTDIR) && !located)
                     ? 127
                     : 126;
        fprintf(stderr, "minish: %s: %s\n", command->argv[0],
                strerror(saved_errno));
    }
    _exit(status);
}

static int launch_pipeline(Shell *shell, const Pipeline *pipeline)
{
    size_t pipe_count = pipeline->ncommands > 0 ? pipeline->ncommands - 1 : 0;
    int (*pipes)[2] = NULL;
    Job *job;
    size_t i;
    size_t launched = 0;
    pid_t pgid = 0;
    int result;
    int launch_barrier[2] = {-1, -1};
    bool terminal_transferred = false;

    if (pipeline->ncommands == 1 && !pipeline->background &&
        is_builtin(pipeline->commands[0].argv[0])) {
        return run_parent_builtin(shell, &pipeline->commands[0]);
    }

    /* Children must not inherit a partially buffered copy of shell output. */
    fflush(NULL);

    if (pipe_count > 0) {
        pipes = xmalloc_array(pipe_count, sizeof(*pipes));
        for (i = 0; i < pipe_count; i++) {
            pipes[i][0] = -1;
            pipes[i][1] = -1;
        }
        for (i = 0; i < pipe_count; i++) {
            if (pipe_retry(pipes[i]) < 0) {
                fprintf(stderr, "minish: pipe: %s\n", strerror(errno));
                close_all_pipes(pipes, pipe_count);
                free(pipes);
                return 1;
            }
        }
    }

    if (shell->interactive && !pipeline->background) {
        int read_flags;
        int write_flags;

        if (pipe_retry(launch_barrier) < 0) {
            fprintf(stderr, "minish: launch barrier: %s\n", strerror(errno));
            close_all_pipes(pipes, pipe_count);
            free(pipes);
            return 1;
        }
        read_flags = fcntl_get_retry(launch_barrier[0], F_GETFD);
        write_flags = fcntl_get_retry(launch_barrier[1], F_GETFD);
        if (read_flags < 0 || write_flags < 0 ||
            fcntl_set_retry(launch_barrier[0], F_SETFD,
                            read_flags | FD_CLOEXEC) < 0 ||
            fcntl_set_retry(launch_barrier[1], F_SETFD,
                            write_flags | FD_CLOEXEC) < 0) {
            fprintf(stderr, "minish: launch barrier flags: %s\n",
                    strerror(errno));
            close(launch_barrier[0]);
            close(launch_barrier[1]);
            close_all_pipes(pipes, pipe_count);
            free(pipes);
            return 1;
        }
    }

    job = xmalloc(sizeof(*job));
    memset(job, 0, sizeof(*job));
    job->nprocesses = pipeline->ncommands;
    job->processes = xmalloc_array(job->nprocesses, sizeof(*job->processes));
    memset(job->processes, 0, job->nprocesses * sizeof(*job->processes));
    job->command = xstrdup(pipeline->display);

    for (i = 0; i < pipeline->ncommands; i++) {
        pid_t pid = fork();
        if (pid == 0) {
            child_execute(shell, pipeline, i, pipes, pipe_count, pgid,
                          launch_barrier[0], launch_barrier[1]);
        }
        if (pid < 0) {
            fprintf(stderr, "minish: fork: %s\n", strerror(errno));
            break;
        }
        if (pgid == 0) {
            pgid = pid;
            job->pgid = pgid;
        }
        if (setpgid(pid, pgid) < 0 && errno != EACCES && errno != ESRCH) {
            fprintf(stderr, "minish: setpgid: %s\n", strerror(errno));
        }
        job->processes[i].pid = pid;
        job->processes[i].state = PROC_RUNNING;
        launched++;
    }
    close_all_pipes(pipes, pipe_count);
    free(pipes);
    if (launch_barrier[0] >= 0) {
        close(launch_barrier[0]);
        launch_barrier[0] = -1;
    }

    if (launched != pipeline->ncommands) {
        if (pgid > 0) {
            (void)kill(-pgid, SIGKILL);
        }
        for (i = 0; i < launched; i++) {
            (void)kill(job->processes[i].pid, SIGKILL);
        }
        if (launch_barrier[1] >= 0) {
            close(launch_barrier[1]);
            launch_barrier[1] = -1;
        }
        for (i = 0; i < launched; i++) {
            while (waitpid(job->processes[i].pid, NULL, 0) < 0 && errno == EINTR) {
                /* retry */
            }
        }
        job_free(job);
        return 1;
    }

    if (pipeline->background) {
        shell_add_job(shell, job);
        if (shell->show_prompt) {
            printf("[%d] %ld\n", job->id, (long)job->pgid);
            fflush(stdout);
        }
        return 0;
    }

    if (launch_barrier[1] >= 0) {
        if (set_terminal_group(shell, job->pgid) < 0) {
            (void)kill(-job->pgid, SIGKILL);
            for (i = 0; i < launched; i++) {
                (void)kill(job->processes[i].pid, SIGKILL);
            }
            close(launch_barrier[1]);
            launch_barrier[1] = -1;
            for (i = 0; i < launched; i++) {
                while (waitpid(job->processes[i].pid, NULL, 0) < 0 &&
                       errno == EINTR) {
                    /* retry */
                }
            }
            job_free(job);
            return 1;
        }
        terminal_transferred = true;
        if (release_launch_barrier(launch_barrier[1], launched) < 0) {
            (void)kill(-job->pgid, SIGKILL);
            for (i = 0; i < launched; i++) {
                (void)kill(job->processes[i].pid, SIGKILL);
            }
            close(launch_barrier[1]);
            launch_barrier[1] = -1;
            for (i = 0; i < launched; i++) {
                while (waitpid(job->processes[i].pid, NULL, 0) < 0 &&
                       errno == EINTR) {
                    /* retry */
                }
            }
            (void)set_terminal_group(shell, shell->shell_pgid);
            job_free(job);
            return 1;
        }
        close(launch_barrier[1]);
        launch_barrier[1] = -1;
    }

    result = put_job_in_foreground(shell, job, false, terminal_transferred);
    if (job_state(job) == JOB_STOPPED) {
        shell_add_job(shell, job);
        if (shell->show_prompt) {
            printf("[%d] Stopped %s\n", job->id, job->command);
            fflush(stdout);
        }
    } else {
        job_free(job);
    }
    return result;
}

static int execute_line(Shell *shell, const char *line)
{
    TokenVec tokens = {0};
    Program program = {0};
    char *error = NULL;
    size_t i;
    int result = shell->last_status;

    if (lex_line(line, &tokens, &error) < 0) {
        fprintf(stderr, "minish: syntax error: %s\n", error);
        free(error);
        token_vec_free(&tokens);
        shell->last_status = 2;
        return 2;
    }
    if (parse_program(line, &tokens, &program, &error) < 0) {
        fprintf(stderr, "minish: syntax error: %s\n", error);
        free(error);
        program_free(&program);
        token_vec_free(&tokens);
        shell->last_status = 2;
        return 2;
    }

    for (i = 0; i < program.len && !shell->exiting; i++) {
        refresh_jobs(shell);
        result = launch_pipeline(shell, &program.pipelines[i]);
        shell->last_status = result;
        if (!program.pipelines[i].background) {
            shell->last_foreground_status = result;
        }
    }
    program_free(&program);
    token_vec_free(&tokens);
    return result;
}

static void initialize_shell(Shell *shell)
{
    bool input_is_terminal;
    pid_t foreground_group;
    pid_t shell_group;
    int flags;

    memset(shell, 0, sizeof(*shell));
    shell->next_job_id = 1;
    shell->terminal_fd = STDIN_FILENO;
    input_is_terminal = isatty(STDIN_FILENO) != 0;
    shell->show_prompt = input_is_terminal && isatty(STDOUT_FILENO) != 0;

    if (pipe_retry(sigchld_pipe) < 0) {
        fprintf(stderr, "minish: signal pipe: %s\n", strerror(errno));
        exit(2);
    }
    flags = fcntl_get_retry(sigchld_pipe[0], F_GETFL);
    if (flags < 0 ||
        fcntl_set_retry(sigchld_pipe[0], F_SETFL, flags | O_NONBLOCK) < 0) {
        fprintf(stderr, "minish: signal pipe flags: %s\n", strerror(errno));
        exit(2);
    }
    flags = fcntl_get_retry(sigchld_pipe[1], F_GETFL);
    if (flags < 0 ||
        fcntl_set_retry(sigchld_pipe[1], F_SETFL, flags | O_NONBLOCK) < 0) {
        fprintf(stderr, "minish: signal pipe flags: %s\n", strerror(errno));
        exit(2);
    }
    if (fcntl_set_retry(sigchld_pipe[0], F_SETFD, FD_CLOEXEC) < 0 ||
        fcntl_set_retry(sigchld_pipe[1], F_SETFD, FD_CLOEXEC) < 0) {
        fprintf(stderr, "minish: signal pipe close-on-exec: %s\n", strerror(errno));
        exit(2);
    }
    set_signal_action(SIGCHLD, sigchld_handler);
    set_signal_action(SIGPIPE, SIG_IGN);

    if (!input_is_terminal) {
        return;
    }

    errno = 0;
    foreground_group = tcgetpgrp_retry(STDIN_FILENO);
    if (foreground_group < 0) {
        if (errno == ENOTTY) {
            return;
        }
        fprintf(stderr, "minish: tcgetpgrp: %s\n", strerror(errno));
        exit(2);
    }
    shell->terminal_fd = fcntl_set_retry(STDIN_FILENO, F_DUPFD,
                                         STDERR_FILENO + 1);
    if (shell->terminal_fd < 0 ||
        fcntl_set_retry(shell->terminal_fd, F_SETFD, FD_CLOEXEC) < 0) {
        fprintf(stderr, "minish: terminal descriptor: %s\n", strerror(errno));
        exit(2);
    }
    shell->interactive = true;
    shell_group = getpgrp();
    while (foreground_group != shell_group) {
        if (kill(-shell_group, SIGTTIN) < 0) {
            fprintf(stderr, "minish: cannot acquire terminal: %s\n", strerror(errno));
            exit(2);
        }
        shell_group = getpgrp();
        foreground_group = tcgetpgrp_retry(shell->terminal_fd);
        if (foreground_group < 0) {
            fprintf(stderr, "minish: tcgetpgrp: %s\n", strerror(errno));
            exit(2);
        }
    }

    set_signal_action(SIGINT, SIG_IGN);
    set_signal_action(SIGQUIT, SIG_IGN);
    set_signal_action(SIGTSTP, SIG_IGN);
    set_signal_action(SIGTTIN, SIG_IGN);
    set_signal_action(SIGTTOU, SIG_IGN);

    shell->shell_pgid = getpid();
    if (setpgid(shell->shell_pgid, shell->shell_pgid) < 0 &&
        errno != EACCES && errno != EPERM) {
        fprintf(stderr, "minish: setpgid: %s\n", strerror(errno));
        exit(2);
    }
    shell->shell_pgid = getpgrp();
    if (tcsetpgrp(shell->terminal_fd, shell->shell_pgid) < 0) {
        fprintf(stderr, "minish: tcsetpgrp: %s\n", strerror(errno));
        exit(2);
    }
    if (tcgetattr_retry(shell->terminal_fd, &shell->shell_modes) < 0) {
        fprintf(stderr, "minish: tcgetattr: %s\n", strerror(errno));
        exit(2);
    }
}

static void shutdown_jobs(Shell *shell)
{
    size_t i;
    struct timespec pause_time;
    int rounds;

    refresh_jobs(shell);
    for (i = 0; i < shell->njobs; i++) {
        Job *job = shell->jobs[i];
        if (job_state(job) != JOB_DONE) {
            (void)kill(-job->pgid, SIGHUP);
            (void)kill(-job->pgid, SIGCONT);
        }
    }

    pause_time.tv_sec = 0;
    pause_time.tv_nsec = 10000000L;
    for (rounds = 0; rounds < 20; rounds++) {
        bool active = false;
        refresh_jobs(shell);
        for (i = 0; i < shell->njobs; i++) {
            if (job_state(shell->jobs[i]) != JOB_DONE) {
                active = true;
                break;
            }
        }
        if (!active) {
            break;
        }
        (void)nanosleep(&pause_time, NULL);
    }

    for (i = 0; i < shell->njobs; i++) {
        Job *job = shell->jobs[i];
        size_t process_index;
        if (job_state(job) != JOB_DONE) {
            (void)kill(-job->pgid, SIGKILL);
        }
        for (process_index = 0; process_index < job->nprocesses;
             process_index++) {
            if (job->processes[process_index].state != PROC_DONE) {
                (void)kill(job->processes[process_index].pid, SIGKILL);
            }
        }
    }
    for (;;) {
        pid_t pid = waitpid(-1, NULL, 0);
        if (pid > 0) {
            continue;
        }
        if (pid < 0 && errno == EINTR) {
            continue;
        }
        break;
    }
    for (i = 0; i < shell->njobs; i++) {
        job_free(shell->jobs[i]);
    }
    free(shell->jobs);
    shell->jobs = NULL;
    shell->njobs = 0;
    if (sigchld_pipe[0] >= 0) {
        close(sigchld_pipe[0]);
        sigchld_pipe[0] = -1;
    }
    if (sigchld_pipe[1] >= 0) {
        close(sigchld_pipe[1]);
        sigchld_pipe[1] = -1;
    }
    if (shell->terminal_fd > STDERR_FILENO) {
        close(shell->terminal_fd);
        shell->terminal_fd = STDIN_FILENO;
    }
}

static int read_command_line(Shell *shell, char **line_out)
{
    StringBuilder line = {0};
    bool contains_nul = false;

    for (;;) {
        struct pollfd descriptors[2];
        int ready;

        descriptors[0].fd = STDIN_FILENO;
        descriptors[0].events = POLLIN | POLLHUP;
        descriptors[0].revents = 0;
        descriptors[1].fd = sigchld_pipe[0];
        descriptors[1].events = POLLIN;
        descriptors[1].revents = 0;

        ready = poll(descriptors, 2, -1);
        if (ready < 0) {
            if (errno == EINTR) {
                refresh_jobs(shell);
                continue;
            }
            fprintf(stderr, "minish: poll: %s\n", strerror(errno));
            free(line.data);
            return -1;
        }

        if ((descriptors[1].revents & POLLIN) != 0) {
            refresh_jobs(shell);
        }
        if ((descriptors[0].revents & (POLLIN | POLLHUP)) != 0) {
            char ch;
            ssize_t count = read(STDIN_FILENO, &ch, 1);
            if (count > 0) {
                if (ch == '\0') {
                    contains_nul = true;
                } else if (ch != '\n') {
                    sb_append(&line, ch);
                }
                if (ch == '\n') {
                    if (contains_nul) {
                        free(line.data);
                        *line_out = NULL;
                        return 2;
                    }
                    *line_out = sb_finish(&line);
                    return 1;
                }
                continue;
            }
            if (count == 0) {
                if (line.len > 0 || contains_nul) {
                    if (contains_nul) {
                        free(line.data);
                        *line_out = NULL;
                        return 2;
                    }
                    *line_out = sb_finish(&line);
                    return 1;
                }
                free(line.data);
                *line_out = NULL;
                return 0;
            }
            if (errno == EINTR || errno == EAGAIN) {
                continue;
            }
            fprintf(stderr, "minish: read: %s\n", strerror(errno));
            free(line.data);
            return -1;
        }
    }
}

static int run_input(Shell *shell)
{
    for (;;) {
        char *line = NULL;
        int read_result;

        refresh_jobs(shell);
        if (shell->show_prompt) {
            fputs("minish$ ", stdout);
            fflush(stdout);
        }
        read_result = read_command_line(shell, &line);
        if (read_result == 2) {
            fputs("minish: syntax error: NUL byte in input\n", stderr);
            shell->last_status = 2;
            continue;
        }
        if (read_result <= 0) {
            if (read_result < 0) {
                shell->last_status = 1;
            }
            break;
        }
        (void)execute_line(shell, line);
        free(line);
        if (shell->exiting) {
            break;
        }
    }
    return shell->exiting ? shell->exit_status : shell->last_status;
}

static int run_command_string(Shell *shell, const char *command)
{
    const char *start = command;
    int result = shell->last_status;

    /* Newlines are command separators in -c input, just as they are on stdin. */
    while (*start != '\0' && !shell->exiting) {
        const char *newline = strchr(start, '\n');
        size_t length = newline == NULL ? strlen(start) : (size_t)(newline - start);
        char *line = xmalloc_terminated(length);
        memcpy(line, start, length);
        line[length] = '\0';
        result = execute_line(shell, line);
        free(line);
        if (newline == NULL) {
            break;
        }
        start = newline + 1;
    }
    return shell->exiting ? shell->exit_status : result;
}

static void print_usage(FILE *stream)
{
    fputs("Usage: minish [-c COMMAND]\n", stream);
}

static void print_help(void)
{
    print_usage(stdout);
    fputs("Execute COMMAND, or read command lines from standard input.\n", stdout);
}

int main(int argc, char **argv)
{
    Shell shell;
    int status;

    if (argc == 2 && strcmp(argv[1], "--help") == 0) {
        print_help();
        return 0;
    }
    if (argc != 1 && argc != 3) {
        print_usage(stderr);
        return 2;
    }
    if (argc == 3 && strcmp(argv[1], "-c") != 0) {
        print_usage(stderr);
        return 2;
    }

    initialize_shell(&shell);
    if (argc == 3) {
        shell.show_prompt = false;
    }
    if (argc == 1) {
        /* Do not read ahead past a command that may give stdin to its child. */
        (void)setvbuf(stdin, NULL, _IONBF, 0);
    }
    if (shell.show_prompt) {
        (void)setvbuf(stdout, NULL, _IOLBF, 0);
    }

    if (argc == 3) {
        status = run_command_string(&shell, argv[2]);
    } else {
        status = run_input(&shell);
    }
    shutdown_jobs(&shell);
    return status;
}
