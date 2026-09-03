#include "minish.h"

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static unsigned failures;

#define CHECK(condition)                                                       \
    do {                                                                       \
        if (!(condition)) {                                                    \
            (void)fprintf(stderr, "%s:%d: CHECK failed: %s\n", __FILE__,      \
                          __LINE__, #condition);                               \
            ++failures;                                                        \
        }                                                                      \
    } while (0)

static TokenList lex_ok(const char *line)
{
    TokenList tokens = {0};
    char error[192] = {0};

    if (lex_line(line, &tokens, error, sizeof(error)) != 0) {
        (void)fprintf(stderr, "lex failed for [%s]: %s\n", line, error);
        ++failures;
    }
    return tokens;
}

static Pipeline parse_ok(const char *line)
{
    TokenList tokens = lex_ok(line);
    Pipeline pipeline = {0};
    char error[192] = {0};

    if (parse_pipeline(&tokens, &pipeline, error, sizeof(error)) != 0) {
        (void)fprintf(stderr, "parse failed for [%s]: %s\n", line, error);
        ++failures;
    }
    token_list_free(&tokens);
    return pipeline;
}

static void test_lex_boundaries(void)
{
    TokenList tokens = lex_ok("echo#literal # comment");

    CHECK(tokens.len == 2);
    if (tokens.len == 2) {
        CHECK(strcmp(tokens.items[0].text, "echo#literal") == 0);
        CHECK(tokens.items[1].type == TOK_END);
    }
    token_list_free(&tokens);

    tokens = lex_ok("x\\|y \"a\\\"b\" ''");
    CHECK(tokens.len == 4);
    if (tokens.len == 4) {
        CHECK(strcmp(tokens.items[0].text, "x|y") == 0);
        CHECK(strcmp(tokens.items[1].text, "a\"b") == 0);
        CHECK(strcmp(tokens.items[2].text, "") == 0);
    }
    token_list_free(&tokens);
}

static void test_lex_failures_are_freeable(void)
{
    const char *bad[] = {"x\\", "'x", "\"x", "\"x\\"};
    size_t i;

    for (i = 0; i < sizeof(bad) / sizeof(bad[0]); ++i) {
        TokenList tokens = {0};
        char error[192] = {0};

        CHECK(lex_line(bad[i], &tokens, error, sizeof(error)) == -1);
        CHECK(error[0] != '\0');
        token_list_free(&tokens);
        token_list_free(&tokens);
    }

    {
        char oversized[4098];
        TokenList tokens = {0};
        char error[192] = {0};

        memset(oversized, 'x', sizeof(oversized) - 1);
        oversized[sizeof(oversized) - 1] = '\0';
        CHECK(lex_line(oversized, &tokens, error, sizeof(error)) == -1);
        token_list_free(&tokens);
    }
}

static void test_parser_owns_strings(void)
{
    TokenList tokens = lex_ok("first a < input | second >> output &");
    Pipeline pipeline = {0};
    char error[192] = {0};

    CHECK(parse_pipeline(&tokens, &pipeline, error, sizeof(error)) == 0);
    token_list_free(&tokens);
    if (pipeline.count == 2) {
        CHECK(strcmp(pipeline.commands[0].argv[0], "first") == 0);
        CHECK(strcmp(pipeline.commands[0].input_path, "input") == 0);
        CHECK(strcmp(pipeline.commands[1].argv[0], "second") == 0);
        CHECK(strcmp(pipeline.commands[1].output_path, "output") == 0);
        CHECK(pipeline.commands[1].append_output);
        CHECK(pipeline.background);
    } else {
        CHECK(pipeline.count == 2);
    }
    pipeline_free(&pipeline);
    pipeline_free(&pipeline);
}

static void test_parser_rejections(void)
{
    const char *bad[] = {"",          "# comment", "x | | y",
                         "x <",       "x < a < b", "x > a > b",
                         "x & y",     "&",         "x | &"};
    size_t i;

    for (i = 0; i < sizeof(bad) / sizeof(bad[0]); ++i) {
        TokenList tokens = lex_ok(bad[i]);
        Pipeline pipeline = {0};
        char error[192] = {0};

        CHECK(parse_pipeline(&tokens, &pipeline, error, sizeof(error)) == -1);
        CHECK(error[0] != '\0');
        pipeline_free(&pipeline);
        token_list_free(&tokens);
    }
}

static Command literal_command(char **arguments)
{
    size_t count = 0;

    while (arguments[count] != NULL) {
        ++count;
    }
    return (Command){.argv = arguments, .argc = count};
}

static int wait_status(pid_t child)
{
    int status;
    pid_t waited;

    do {
        waited = waitpid(child, &status, 0);
    } while (waited < 0 && errno == EINTR);
    if (waited != child || !WIFEXITED(status)) {
        return -1;
    }
    return WEXITSTATUS(status);
}

static int write_all(int descriptor, const char *text)
{
    size_t remaining = strlen(text);

    while (remaining > 0) {
        ssize_t written = write(descriptor, text, remaining);

        if (written < 0 && errno == EINTR) {
            continue;
        }
        if (written <= 0) {
            return -1;
        }
        text += (size_t)written;
        remaining -= (size_t)written;
    }
    return 0;
}

static int file_equals(const char *path, const char *expected)
{
    char buffer[64];
    int descriptor = open(path, O_RDONLY);
    ssize_t length;

    if (descriptor < 0) {
        return 0;
    }
    do {
        length = read(descriptor, buffer, sizeof(buffer));
    } while (length < 0 && errno == EINTR);
    (void)close(descriptor);
    return length >= 0 && (size_t)length == strlen(expected) &&
           memcmp(buffer, expected, (size_t)length) == 0;
}

static void test_closed_standard_descriptors(void)
{
    const ShellContext context = {
        .interactive = false,
        .terminal_fd = 0,
        .shell_pgid = 0,
    };
    char input_path[] = ".minish-fd-input-XXXXXX";
    char input_output_path[] = ".minish-fd-input-output-XXXXXX";
    char pipeline_output_path[] = ".minish-fd-pipeline-output-XXXXXX";
    int input = mkstemp(input_path);
    int input_output = mkstemp(input_output_path);
    int pipeline_output = mkstemp(pipeline_output_path);
    pid_t child;

    CHECK(input >= 0);
    CHECK(input_output >= 0);
    CHECK(pipeline_output >= 0);
    if (input < 0 || input_output < 0 || pipeline_output < 0) {
        if (input >= 0) {
            (void)close(input);
            (void)unlink(input_path);
        }
        if (input_output >= 0) {
            (void)close(input_output);
            (void)unlink(input_output_path);
        }
        if (pipeline_output >= 0) {
            (void)close(pipeline_output);
            (void)unlink(pipeline_output_path);
        }
        return;
    }
    CHECK(write_all(input, "input-redirection") == 0);
    (void)close(input);
    (void)close(input_output);
    (void)close(pipeline_output);

    child = fork();
    CHECK(child >= 0);
    if (child == 0) {
        char *arguments[] = {"/bin/cat", NULL};
        Command command = literal_command(arguments);
        Pipeline pipeline = {.commands = &command, .count = 1};

        command.input_path = input_path;
        command.output_path = input_output_path;
        (void)close(STDIN_FILENO);
        _exit(execute_pipeline(&pipeline, &context) == 0 ? 0 : 1);
    }
    if (child > 0) {
        CHECK(wait_status(child) == 0);
        CHECK(file_equals(input_output_path, "input-redirection"));
    }

    child = fork();
    CHECK(child >= 0);
    if (child == 0) {
        char *producer_arguments[] = {"/usr/bin/printf", "pipeline-data", NULL};
        char *consumer_arguments[] = {"/bin/cat", NULL};
        Command commands[] = {
            literal_command(producer_arguments),
            literal_command(consumer_arguments),
        };
        Pipeline pipeline = {.commands = commands, .count = 2};

        commands[1].output_path = pipeline_output_path;
        (void)close(STDIN_FILENO);
        (void)close(STDOUT_FILENO);
        _exit(execute_pipeline(&pipeline, &context) == 0 ? 0 : 1);
    }
    if (child > 0) {
        CHECK(wait_status(child) == 0);
        CHECK(file_equals(pipeline_output_path, "pipeline-data"));
    }

    (void)unlink(input_path);
    (void)unlink(input_output_path);
    (void)unlink(pipeline_output_path);
}

static void test_execution_status_and_reaping(void)
{
    const ShellContext context = {
        .interactive = false,
        .terminal_fd = 0,
        .shell_pgid = 0,
    };
    char *false_arguments[] = {"/bin/false", NULL};
    char *missing_arguments[] = {"minish-command-that-does-not-exist", NULL};
    char *true_arguments[] = {"/bin/true", NULL};
    Command command = literal_command(false_arguments);
    Pipeline pipeline = {.commands = &command, .count = 1};
    struct timespec pause = {.tv_sec = 0, .tv_nsec = 10000000L};
    size_t i;
    size_t reaped = 0;

    CHECK(execute_pipeline(&pipeline, &context) == 1);
    command = literal_command(missing_arguments);
    CHECK(execute_pipeline(&pipeline, &context) == 127);

    command = literal_command(true_arguments);
    pipeline.background = true;
    CHECK(execute_pipeline(&pipeline, &context) == 0);
    for (i = 0; i < 50 && reaped == 0; ++i) {
        (void)nanosleep(&pause, NULL);
        reaped += shell_reap_background();
    }
    CHECK(reaped == 1);
}

static void test_parse_convenience(void)
{
    Pipeline pipeline = parse_ok("a>b<c");

    CHECK(pipeline.count == 1);
    if (pipeline.count == 1) {
        CHECK(strcmp(pipeline.commands[0].argv[0], "a") == 0);
        CHECK(strcmp(pipeline.commands[0].output_path, "b") == 0);
        CHECK(strcmp(pipeline.commands[0].input_path, "c") == 0);
    }
    pipeline_free(&pipeline);
}

int main(void)
{
    test_lex_boundaries();
    test_lex_failures_are_freeable();
    test_parser_owns_strings();
    test_parser_rejections();
    test_execution_status_and_reaping();
    test_closed_standard_descriptors();
    test_parse_convenience();

    if (failures != 0) {
        (void)fprintf(stderr, "%u sealed reference check(s) failed\n", failures);
        return EXIT_FAILURE;
    }
    (void)puts("sealed reference unit tests: PASS");
    return EXIT_SUCCESS;
}
