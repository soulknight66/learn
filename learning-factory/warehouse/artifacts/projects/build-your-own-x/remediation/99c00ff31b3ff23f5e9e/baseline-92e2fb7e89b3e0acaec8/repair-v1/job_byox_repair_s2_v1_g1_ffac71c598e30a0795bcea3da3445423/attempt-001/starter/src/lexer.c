#include "lexer.h"

void lexer_init(struct lexer *lexer, const char *source, size_t length) {
    lexer->source = source;
    lexer->length = length;
    lexer->offset = 0;
    lexer->line = 1;
    lexer->column = 1;
}

struct token lexer_next(struct lexer *lexer) {
    struct token token;

    token.kind = lexer->offset == lexer->length ? TOKEN_EOF : TOKEN_ERROR;
    token.begin = lexer->source + lexer->offset;
    token.length = 0;
    token.line = lexer->line;
    token.column = lexer->column;
    token.integer = 0;

    /* TODO: skip trivia, scan all token forms, and advance line/column. */
    return token;
}
