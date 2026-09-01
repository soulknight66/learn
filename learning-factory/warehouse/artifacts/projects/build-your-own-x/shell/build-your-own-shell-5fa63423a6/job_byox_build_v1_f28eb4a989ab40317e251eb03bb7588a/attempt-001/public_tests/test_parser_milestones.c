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

int main(void)
{
    test_quotes_and_escape();
    test_quote_edges();
    test_pipeline_redirection_background();
    test_syntax_errors();
    if (failures != 0) {
        (void)fprintf(stderr, "%d milestone assertion(s) failed\n", failures);
        return 1;
    }
    (void)puts("parser milestones: PASS");
    return 0;
}
