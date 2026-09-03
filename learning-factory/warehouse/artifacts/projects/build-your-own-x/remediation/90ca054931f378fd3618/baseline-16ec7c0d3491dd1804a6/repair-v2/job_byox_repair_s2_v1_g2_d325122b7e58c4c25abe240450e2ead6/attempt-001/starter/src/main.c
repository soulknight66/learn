#include "ember.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int read_source(const char *path, char **data, size_t *length) {
    FILE *stream = fopen(path, "rb");
    long size;
    size_t got;
    if (stream == NULL) {
        fprintf(stderr, "%s:1:1: cannot open: %s\n", path, strerror(errno));
        return 1;
    }
    if (fseek(stream, 0L, SEEK_END) != 0 || (size = ftell(stream)) < 0L ||
        fseek(stream, 0L, SEEK_SET) != 0) {
        fprintf(stderr, "%s:1:1: cannot measure source\n", path);
        fclose(stream);
        return 1;
    }
    if ((unsigned long)size > EMBER_SOURCE_MAX) {
        fprintf(stderr, "%s:1:1: source exceeds 1048576 bytes\n", path);
        fclose(stream);
        return 1;
    }
    *data = malloc((size_t)size + 1U);
    if (*data == NULL) {
        fprintf(stderr, "%s:1:1: out of memory\n", path);
        fclose(stream);
        return 1;
    }
    got = fread(*data, 1U, (size_t)size, stream);
    if (got != (size_t)size || fclose(stream) != 0) {
        fprintf(stderr, "%s:1:1: cannot read complete source\n", path);
        free(*data);
        *data = NULL;
        return 1;
    }
    (*data)[got] = '\0';
    *length = got;
    return 0;
}

static int print_tokens(const char *path, const char *source, size_t length) {
    Lexer lexer;
    lexer_init(&lexer, source, length);
    for (;;) {
        Token token = lexer_next(&lexer);
        if (token.kind == TOK_ERROR) {
            fprintf(stderr, "%s:%zu:%zu: %s\n", path, token.line,
                    token.column, token.message);
            return 1;
        }
        printf("%zu:%zu %s %.*s\n", token.line, token.column,
               token_kind_name(token.kind), (int)token.length, token.start);
        if (token.kind == TOK_EOF) {
            return 0;
        }
    }
}

static void usage(const char *program) {
    fprintf(stderr, "usage: %s --tokens SOURCE\n", program);
    fprintf(stderr, "       %s --check SOURCE\n", program);
    fprintf(stderr, "       %s SOURCE [-- INTEGER ...]\n", program);
}

int main(int argc, char **argv) {
    const char *path;
    char *source = NULL;
    size_t length = 0U;
    int token_mode = 0;
    int status;

    if (argc == 3 && strcmp(argv[1], "--tokens") == 0) {
        token_mode = 1;
        path = argv[2];
    } else if (argc == 3 && strcmp(argv[1], "--check") == 0) {
        path = argv[2];
    } else if (argc >= 2 && argv[1][0] != '-') {
        path = argv[1];
    } else {
        usage(argv[0]);
        return 2;
    }

    if (read_source(path, &source, &length) != 0) {
        return 1;
    }
    if (token_mode) {
        status = print_tokens(path, source, length);
    } else {
        Bytecode code;
        char error[512];
        status = ember_compile(path, source, length, &code, error,
                               sizeof(error));
        if (status != 0) {
            fprintf(stderr, "%s\n", error);
        }
    }
    free(source);
    return status;
}
