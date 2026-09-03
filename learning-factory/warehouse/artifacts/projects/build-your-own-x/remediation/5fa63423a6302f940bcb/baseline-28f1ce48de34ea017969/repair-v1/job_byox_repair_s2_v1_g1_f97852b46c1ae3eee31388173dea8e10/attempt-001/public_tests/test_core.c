#include "minish.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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
    char error[160] = {0};
    int result = lex_line(line, &tokens, error, sizeof(error));

    if (result != 0) {
        (void)fprintf(stderr, "unexpected lex failure for [%s]: %s\n", line,
                      error);
        ++failures;
    }
    return tokens;
}

static void test_lex_words_and_quotes(void)
{
    TokenList tokens = lex_ok("echo \"a b\" 'c' d\\ e # ignored\n");

    if (tokens.len == 5) {
        CHECK(tokens.items[0].type == TOK_WORD);
        CHECK(strcmp(tokens.items[0].text, "echo") == 0);
        CHECK(strcmp(tokens.items[1].text, "a b") == 0);
        CHECK(strcmp(tokens.items[2].text, "c") == 0);
        CHECK(strcmp(tokens.items[3].text, "d e") == 0);
        CHECK(tokens.items[4].type == TOK_END);
    } else {
        CHECK(tokens.len == 5);
    }
    token_list_free(&tokens);
}

static void test_lex_operators_and_empty_word(void)
{
    TokenList tokens = lex_ok("a|b>>out&");
    const TokenType expected[] = {TOK_WORD, TOK_PIPE, TOK_WORD,
                                  TOK_REDIR_APPEND, TOK_WORD, TOK_AMP, TOK_END};
    size_t i;

    CHECK(tokens.len == sizeof(expected) / sizeof(expected[0]));
    for (i = 0; i < tokens.len && i < sizeof(expected) / sizeof(expected[0]);
         ++i) {
        CHECK(tokens.items[i].type == expected[i]);
    }
    token_list_free(&tokens);

    tokens = lex_ok("printf ''");
    if (tokens.len == 3) {
        CHECK(tokens.items[1].type == TOK_WORD);
        CHECK(strcmp(tokens.items[1].text, "") == 0);
    } else {
        CHECK(tokens.len == 3);
    }
    token_list_free(&tokens);
}

static void test_lex_error(void)
{
    TokenList tokens = {0};
    char error[160] = {0};

    CHECK(lex_line("echo 'unfinished", &tokens, error, sizeof(error)) == -1);
    CHECK(error[0] != '\0');
    token_list_free(&tokens);
}

static void test_parse_pipeline(void)
{
    TokenList tokens = lex_ok("printf hello | wc -c > count &");
    Pipeline pipeline = {0};
    char error[160] = {0};

    CHECK(parse_pipeline(&tokens, &pipeline, error, sizeof(error)) == 0);
    if (pipeline.count == 2) {
        CHECK(pipeline.background);
        CHECK(pipeline.commands[0].argc == 2);
        CHECK(strcmp(pipeline.commands[0].argv[1], "hello") == 0);
        CHECK(pipeline.commands[1].argc == 2);
        CHECK(strcmp(pipeline.commands[1].output_path, "count") == 0);
        CHECK(!pipeline.commands[1].append_output);
    } else {
        CHECK(pipeline.count == 2);
    }
    pipeline_free(&pipeline);
    token_list_free(&tokens);
}

static void expect_parse_error(const char *line)
{
    TokenList tokens = lex_ok(line);
    Pipeline pipeline = {0};
    char error[160] = {0};

    CHECK(parse_pipeline(&tokens, &pipeline, error, sizeof(error)) == -1);
    CHECK(error[0] != '\0');
    pipeline_free(&pipeline);
    token_list_free(&tokens);
}

static void test_parse_errors(void)
{
    expect_parse_error("| echo x");
    expect_parse_error("echo x |");
    expect_parse_error("echo >");
    expect_parse_error("echo > a >> b");
    expect_parse_error("echo & later");
    expect_parse_error("# only a comment");
}

int main(void)
{
    test_lex_words_and_quotes();
    test_lex_operators_and_empty_word();
    test_lex_error();
    test_parse_pipeline();
    test_parse_errors();

    if (failures != 0) {
        (void)fprintf(stderr, "%u public core check(s) failed\n", failures);
        return EXIT_FAILURE;
    }
    (void)puts("public core tests: PASS");
    return EXIT_SUCCESS;
}
