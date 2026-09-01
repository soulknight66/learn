#include "byosh.h"

#include <stdio.h>
#include <string.h>

static int failures;

#define CHECK(condition, message)                                              \
    do {                                                                       \
        if (!(condition)) {                                                    \
            (void)fprintf(stderr, "FAIL: %s (line %d)\n", message, __LINE__); \
            ++failures;                                                        \
        }                                                                      \
    } while (0)

static void test_empty(void)
{
    char input[] = "  \t\n";
    char error[64];
    struct byosh_pipeline pipeline;
    enum byosh_parse_status status;

    status = byosh_parse_line(input, &pipeline, error, sizeof(error));
    CHECK(status == BYOSH_PARSE_EMPTY, "blank input is empty");
    CHECK(pipeline.command_count == 0U, "blank input has no commands");
}

static void test_plain_words(void)
{
    char input[] = "printf  hello\tworld\n";
    char error[64];
    struct byosh_pipeline pipeline;
    enum byosh_parse_status status;

    status = byosh_parse_line(input, &pipeline, error, sizeof(error));
    CHECK(status == BYOSH_PARSE_OK, "plain words parse");
    CHECK(pipeline.command_count == 1U, "one command is produced");
    CHECK(pipeline.commands[0].argc == 3U, "three arguments are produced");
    CHECK(strcmp(pipeline.commands[0].argv[0], "printf") == 0,
          "argv[0] is preserved");
    CHECK(strcmp(pipeline.commands[0].argv[2], "world") == 0,
          "last word is preserved");
    CHECK(pipeline.commands[0].argv[3] == NULL, "argv is null terminated");
}

static void test_invalid_call(void)
{
    char error[64];
    struct byosh_pipeline pipeline;

    CHECK(byosh_parse_line(NULL, &pipeline, error, sizeof(error)) ==
              BYOSH_PARSE_ERROR,
          "null input is rejected");
    CHECK(error[0] != '\0', "invalid call reports an error");
}

int main(void)
{
    test_empty();
    test_plain_words();
    test_invalid_call();
    if (failures != 0) {
        (void)fprintf(stderr, "%d baseline assertion(s) failed\n", failures);
        return 1;
    }
    (void)puts("baseline parser contract: PASS");
    return 0;
}
