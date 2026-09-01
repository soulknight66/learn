#ifndef BYOSH_SHELL_H
#define BYOSH_SHELL_H

#include <stdbool.h>
#include <signal.h>
#include <stddef.h>
#include <sys/types.h>
#include <termios.h>

typedef enum {
    TOK_WORD,
    TOK_PIPE,
    TOK_REDIR_IN,
    TOK_REDIR_OUT,
    TOK_REDIR_APPEND,
    TOK_AMP,
    TOK_END
} TokenType;

typedef struct {
    TokenType type;
    char *text;
    size_t position;
} Token;

typedef struct {
    Token *items;
    size_t count;
    size_t capacity;
} TokenList;

typedef enum {
    REDIR_INPUT,
    REDIR_OUTPUT,
    REDIR_APPEND
} RedirectionType;

typedef struct {
    RedirectionType type;
    char *path;
} Redirection;

typedef struct {
    char **argv;
    size_t argc;
    size_t argv_capacity;
    Redirection *redirections;
    size_t redirection_count;
    size_t redirection_capacity;
} Command;

typedef struct {
    Command *commands;
    size_t command_count;
    size_t command_capacity;
    bool background;
    char *source;
} Pipeline;

typedef struct {
    pid_t pid;
    bool completed;
    bool stopped;
    int wait_status;
} ProcessRecord;

typedef enum {
    JOB_RUNNING,
    JOB_STOPPED,
    JOB_DONE
} JobState;

typedef struct Job {
    int id;
    pid_t pgid;
    char *command;
    ProcessRecord *processes;
    size_t process_count;
    JobState state;
    bool job_control_visible;
    struct termios terminal_modes;
    bool terminal_modes_valid;
    struct Job *next;
} Job;

typedef struct {
    Job *jobs;
    int next_job_id;
    bool interactive;
    int terminal_fd;
    pid_t shell_pgid;
    struct termios shell_terminal_modes;
    int sigchld_read_fd;
    int sigchld_write_fd;
    sigset_t inherited_signal_mask;
    sigset_t child_signal_mask;
    bool should_exit;
    int exit_status;
    int last_status;
} Shell;

typedef enum {
    BUILTIN_NONE,
    BUILTIN_CD,
    BUILTIN_PWD,
    BUILTIN_EXIT,
    BUILTIN_JOBS,
    BUILTIN_FG,
    BUILTIN_BG
} BuiltinKind;

int lex_line(const char *line, TokenList *tokens, char **error_message);
void token_list_free(TokenList *tokens);

int parse_tokens(const TokenList *tokens, const char *source,
                 Pipeline *pipeline, char **error_message);
void pipeline_free(Pipeline *pipeline);

BuiltinKind builtin_identify(const Command *command);
int builtin_run(Shell *shell, const Command *command, bool in_parent);

int shell_initialize(Shell *shell);
void shell_destroy(Shell *shell);
int shell_execute_pipeline(Shell *shell, const Pipeline *pipeline);
void shell_reap_jobs(Shell *shell, bool notify);
int shell_builtin_jobs(Shell *shell);
int shell_builtin_fg(Shell *shell, const char *job_spec);
int shell_builtin_bg(Shell *shell, const char *job_spec);

#endif
