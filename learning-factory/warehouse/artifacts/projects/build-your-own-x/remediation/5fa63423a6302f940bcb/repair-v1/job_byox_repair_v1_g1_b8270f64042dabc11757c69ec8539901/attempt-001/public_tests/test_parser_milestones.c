#include "byosh.h"

#include <stdio.h>
#include <string.h>

static int failures;

#define EXPECT(condition, label)                                      \
    do {                                                               \
        if (!(condition)) {                                            \
            (void)fprintf(stderr, "FAIL: %s\n", label);               \
            ++failures;                                                \
        }                                                              \
    } while (0)

static struct byosh_pipeline parse_ok(char *input, const char *label)
{
    struct byosh_pipeline pipeline;
    char error[128];
    enum byosh_parse_status status;

    status = byosh_parse_line(input, &pipeline, error, sizeof(error));
    if (status != BYOSH_PARSE_OK) {
        (void)fprintf(stderr, "FAIL: %s: parse status %d (%s)\n",
                      label, (int)status, error);
        ++failures;
    }
    return pipeline;
}

static void build_repeated_words(char *buffer, size_t capacity,
                                 size_t count, const char *separator)
{
    size_t offset = 0U;
    size_t index;

    buffer[0] = '\0';
    for (index = 0U; index < count; ++index) {
        const char *prefix = index == 0U ? "" : separator;
        int written = snprintf(buffer + offset, capacity - offset,
                               "%sx", prefix);

        if (written < 0 || (size_t)written >= capacity - offset) {
            (void)fprintf(stderr, "FAIL: capacity fixture overflow\n");
            ++failures;
            buffer[0] = '\0';
            return;
        }
        offset += (size_t)written;
    }
}

static void test_quotes_and_escape(void)
{
    char input[] = "printf '%s %s' \"hello world\" escaped\\ space";
    struct byosh_pipeline pipeline = parse_ok(input, "quotes and escape");

    EXPECT(pipeline.command_count == 1U, "quotes: one command");
    EXPECT(pipeline.commands[0].argc == 4U, "quotes: four arguments");
    if (pipeline.commands[0].argc >= 4U) {
        EXPECT(strcmp(pipeline.commands[0].argv[1], "%s %s") == 0,
               "single quotes are removed");
        EXPECT(strcmp(pipeline.commands[0].argv[2], "hello world") == 0,
               "double quotes group whitespace");
        EXPECT(strcmp(pipeline.commands[0].argv[3], "escaped space") == 0,
               "backslash escapes whitespace");
    }
}

static void test_quote_edges(void)
{
    char input[] = "printf x\"\"y '' a\" b\"c \"a\\\\b\" 'c\\\\d'";
    struct byosh_pipeline pipeline = parse_ok(input, "quote edge cases");

    EXPECT(pipeline.command_count == 1U, "quote edges: one command");
    EXPECT(pipeline.commands[0].argc == 6U, "quote edges: six arguments");
    if (pipeline.commands[0].argc >= 6U) {
        EXPECT(strcmp(pipeline.commands[0].argv[1], "xy") == 0,
               "adjacent fragments form one word");
        EXPECT(strcmp(pipeline.commands[0].argv[2], "") == 0,
               "empty quotes form an empty argument");
        EXPECT(strcmp(pipeline.commands[0].argv[3], "a bc") == 0,
               "quoted and unquoted fragments concatenate");
        EXPECT(strcmp(pipeline.commands[0].argv[4], "a\\b") == 0,
               "backslash is literal in double quotes");
        EXPECT(strcmp(pipeline.commands[0].argv[5], "c\\d") == 0,
               "backslash is literal in single quotes");
    }
}

static void test_pipeline_redirection_background(void)
{
    char input[] = "cat < input.txt | tr a-z A-Z >> output.txt &";
    struct byosh_pipeline pipeline = parse_ok(input, "pipeline syntax");

    EXPECT(pipeline.command_count == 2U, "pipe creates two commands");
    EXPECT(pipeline.background == 1, "trailing ampersand marks background");
    if (pipeline.command_count >= 2U) {
        EXPECT(strcmp(pipeline.commands[0].input_path, "input.txt") == 0,
               "input redirection is attached to first command");
        EXPECT(strcmp(pipeline.commands[1].output_path, "output.txt") == 0,
               "output redirection is attached to second command");
        EXPECT(pipeline.commands[1].append_output == 1,
               "double greater-than selects append mode");
    }
}

static void test_syntax_errors(void)
{
    static const char *const cases[] = {
        "echo 'unterminated",
        "| echo no",
        "echo no |",
        "echo >",
        "echo & later",
        "echo trailing\\",
        "echo > one > two",
        "cat < one < two"
    };
    size_t index;

    for (index = 0U; index < sizeof(cases) / sizeof(cases[0]); ++index) {
        char input[80];
        char error[128];
        struct byosh_pipeline pipeline;
        enum byosh_parse_status status;

        (void)snprintf(input, sizeof(input), "%s", cases[index]);
        status = byosh_parse_line(input, &pipeline, error, sizeof(error));
        EXPECT(status == BYOSH_PARSE_ERROR, "malformed syntax is rejected");
        EXPECT(error[0] != '\0', "malformed syntax has a diagnostic");
    }
}

static void test_documented_capacity_boundaries(void)
{
    char exact_arguments[(BYOSH_MAX_ARGS + 2U) * 3U];
    char excess_arguments[(BYOSH_MAX_ARGS + 3U) * 3U];
    char exact_commands[(BYOSH_MAX_COMMANDS + 2U) * 3U];
    char excess_commands[(BYOSH_MAX_COMMANDS + 3U) * 3U];
    char error[128];
    struct byosh_pipeline pipeline;
    enum byosh_parse_status status;

    build_repeated_words(exact_arguments, sizeof(exact_arguments),
                         BYOSH_MAX_ARGS, " ");
    byosh_pipeline_init(&pipeline);
    error[0] = '\0';
    status = byosh_parse_line(exact_arguments, &pipeline,
                              error, sizeof(error));
    EXPECT(status == BYOSH_PARSE_OK,
           "exact argument capacity is accepted");
    EXPECT(pipeline.command_count == 1U,
           "exact argument capacity produces one command");
    if (pipeline.command_count == 1U) {
        EXPECT(pipeline.commands[0].argc == BYOSH_MAX_ARGS,
               "all arguments at the capacity boundary are retained");
        EXPECT(pipeline.commands[0].argv[BYOSH_MAX_ARGS] == NULL,
               "boundary argv remains null terminated");
    }

    build_repeated_words(excess_arguments, sizeof(excess_arguments),
                         BYOSH_MAX_ARGS + 1U, " ");
    byosh_pipeline_init(&pipeline);
    error[0] = '\0';
    status = byosh_parse_line(excess_arguments, &pipeline,
                              error, sizeof(error));
    EXPECT(status == BYOSH_PARSE_ERROR,
           "argument capacity overflow is rejected");
    EXPECT(error[0] != '\0',
           "argument capacity overflow has a diagnostic");
    EXPECT(pipeline.command_count == 0U,
           "argument capacity overflow leaves no partial pipeline");

    build_repeated_words(exact_commands, sizeof(exact_commands),
                         BYOSH_MAX_COMMANDS, "|");
    byosh_pipeline_init(&pipeline);
    error[0] = '\0';
    status = byosh_parse_line(exact_commands, &pipeline,
                              error, sizeof(error));
    EXPECT(status == BYOSH_PARSE_OK,
           "exact command capacity is accepted");
    EXPECT(pipeline.command_count == BYOSH_MAX_COMMANDS,
           "all commands at the capacity boundary are retained");

    build_repeated_words(excess_commands, sizeof(excess_commands),
                         BYOSH_MAX_COMMANDS + 1U, "|");
    byosh_pipeline_init(&pipeline);
    error[0] = '\0';
    status = byosh_parse_line(excess_commands, &pipeline,
                              error, sizeof(error));
    EXPECT(status == BYOSH_PARSE_ERROR,
           "command capacity overflow is rejected");
    EXPECT(error[0] != '\0',
           "command capacity overflow has a diagnostic");
    EXPECT(pipeline.command_count == 0U,
           "command capacity overflow leaves no partial pipeline");
}

int main(void)
{
    test_quotes_and_escape();
    test_quote_edges();
    test_pipeline_redirection_background();
    test_syntax_errors();
    test_documented_capacity_boundaries();
    if (failures != 0) {
        (void)fprintf(stderr, "%d milestone assertion(s) failed\n", failures);
        return 1;
    }
    (void)puts("parser milestones: PASS");
    return 0;
}
