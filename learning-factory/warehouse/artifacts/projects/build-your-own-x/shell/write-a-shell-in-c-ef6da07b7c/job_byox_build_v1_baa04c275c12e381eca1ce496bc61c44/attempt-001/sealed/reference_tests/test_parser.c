#include "msh.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(condition)                                                        \
    do {                                                                        \
        if (!(condition)) {                                                     \
            (void)fprintf(stderr, "CHECK failed at %s:%d: %s\n",             \
                          __FILE__, __LINE__, #condition);                       \
            exit(1);                                                            \
        }                                                                       \
    } while (0)

static msh_pipeline parse_ok(const char *line)
{
    msh_pipeline pipeline;
    char error[160];

    CHECK(msh_parse_line(line, &pipeline, error, sizeof(error)) == MSH_PARSE_OK);
    return pipeline;
}

static void test_empty_input(void)
{
    msh_pipeline pipeline;
    char error[160];

    CHECK(msh_parse_line(" \t\n", &pipeline, error, sizeof(error)) == MSH_PARSE_EMPTY);
    CHECK(pipeline.commands == NULL);
    CHECK(pipeline.count == 0);
    CHECK(pipeline.background == 0);
}

static void test_word_formation(void)
{
    msh_pipeline pipeline = parse_ok("run \"two words\" 'three four' a\\ b \"\" x''y");

    CHECK(pipeline.count == 1);
    CHECK(pipeline.commands[0].argc == 6);
    CHECK(strcmp(pipeline.commands[0].argv[0], "run") == 0);
    CHECK(strcmp(pipeline.commands[0].argv[1], "two words") == 0);
    CHECK(strcmp(pipeline.commands[0].argv[2], "three four") == 0);
    CHECK(strcmp(pipeline.commands[0].argv[3], "a b") == 0);
    CHECK(strcmp(pipeline.commands[0].argv[4], "") == 0);
    CHECK(strcmp(pipeline.commands[0].argv[5], "xy") == 0);
    CHECK(pipeline.commands[0].argv[6] == NULL);
    msh_pipeline_destroy(&pipeline);
}

static void test_pipeline_and_background(void)
{
    msh_pipeline pipeline = parse_ok("printf x|cat|wc -c&");

    CHECK(pipeline.count == 3);
    CHECK(pipeline.background == 1);
    CHECK(pipeline.commands[0].argc == 2);
    CHECK(strcmp(pipeline.commands[1].argv[0], "cat") == 0);
    CHECK(pipeline.commands[2].argc == 2);
    CHECK(strcmp(pipeline.commands[2].argv[1], "-c") == 0);
    msh_pipeline_destroy(&pipeline);
}

static void test_quoted_operators(void)
{
    msh_pipeline pipeline = parse_ok("printf '%s' '|' \"&\"");

    CHECK(pipeline.count == 1);
    CHECK(pipeline.background == 0);
    CHECK(pipeline.commands[0].argc == 4);
    CHECK(strcmp(pipeline.commands[0].argv[2], "|") == 0);
    CHECK(strcmp(pipeline.commands[0].argv[3], "&") == 0);
    msh_pipeline_destroy(&pipeline);
}

static void test_syntax_errors(void)
{
    static const char *const bad_lines[] = {
        "| one", "one |", "one || two", "&", "one & two",
        "one &&", "'unterminated", "\"unterminated", "trailing\\"
    };
    size_t index;

    for (index = 0; index < sizeof(bad_lines) / sizeof(bad_lines[0]); ++index) {
        msh_pipeline pipeline;
        char error[160] = "";

        CHECK(msh_parse_line(bad_lines[index], &pipeline, error, sizeof(error)) ==
              MSH_PARSE_ERROR);
        CHECK(error[0] != '\0');
        CHECK(pipeline.commands == NULL);
        CHECK(pipeline.count == 0);
        CHECK(pipeline.background == 0);
    }
}

static void test_long_word(void)
{
    const size_t length = 65536;
    char *input = malloc(length + 1);
    msh_pipeline pipeline;

    CHECK(input != NULL);
    memset(input, 'q', length);
    input[length] = '\0';
    pipeline = parse_ok(input);
    CHECK(pipeline.commands[0].argc == 1);
    CHECK(strlen(pipeline.commands[0].argv[0]) == length);
    msh_pipeline_destroy(&pipeline);
    free(input);
}

int main(void)
{
    test_empty_input();
    test_word_formation();
    test_pipeline_and_background();
    test_quoted_operators();
    test_syntax_errors();
    test_long_word();
    (void)puts("parser_tests: 6 cases passed");
    return 0;
}
