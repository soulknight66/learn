#include "minish.h"

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

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
    test_parse_convenience();

    if (failures != 0) {
        (void)fprintf(stderr, "%u sealed reference check(s) failed\n", failures);
        return EXIT_FAILURE;
    }
    (void)puts("sealed reference unit tests: PASS");
    return EXIT_SUCCESS;
}
