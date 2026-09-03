#include "lexer.h"

#include <inttypes.h>
#include <stdio.h>
#include <string.h>

struct expected_token {
    enum token_kind kind;
    const char *text;
    uint32_t line;
    uint32_t column;
    int64_t integer;
};

int main(void) {
    static const char source[] = " # comment\nlet value = 42 != 0;\n";
    static const struct expected_token expected[] = {
        {TOKEN_LET, "let", 2, 1, 0},
        {TOKEN_IDENTIFIER, "value", 2, 5, 0},
        {TOKEN_ASSIGN, "=", 2, 11, 0},
        {TOKEN_INTEGER, "42", 2, 13, 42},
        {TOKEN_BANG_EQUAL, "!=", 2, 16, 0},
        {TOKEN_INTEGER, "0", 2, 19, 0},
        {TOKEN_SEMICOLON, ";", 2, 20, 0},
        {TOKEN_EOF, "", 3, 1, 0},
    };
    struct lexer lexer;
    size_t index;

    lexer_init(&lexer, source, sizeof(source) - 1u);
    for (index = 0; index < sizeof(expected) / sizeof(expected[0]); index++) {
        const struct expected_token *want = &expected[index];
        struct token observed = lexer_next(&lexer);
        size_t wanted_length = strlen(want->text);
        if (observed.kind != want->kind || observed.length != wanted_length ||
            observed.line != want->line || observed.column != want->column ||
            observed.integer != want->integer ||
            memcmp(observed.begin, want->text, wanted_length) != 0) {
            fprintf(stderr,
                    "token %zu mismatch: kind=%d text='%.*s' location=%" PRIu32
                    ":%" PRIu32 " integer=%" PRId64 "\n",
                    index, (int)observed.kind, (int)observed.length,
                    observed.begin, observed.line, observed.column,
                    observed.integer);
            return 1;
        }
    }
    puts("lexer milestone: 8/8 token checks passed");
    return 0;
}
