#include "sprig.h"

#include <errno.h>
#include <inttypes.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
    EXIT_USAGE_ERROR = 64,
    EXIT_COMPILE_ERROR = 65,
    EXIT_RUNTIME_ERROR = 70,
    EXIT_IO_ERROR = 74
};

static int read_source(const char *path, unsigned char **source,
                       size_t *length) {
    FILE *input;
    unsigned char *buffer;
    size_t count;

    input = fopen(path, "rb");
    if (input == NULL) {
        fprintf(stderr, "%s: error: cannot open input: %s\n",
                path, strerror(errno));
        return 0;
    }
    buffer = (unsigned char *)malloc(SPRIG_MAX_SOURCE + 1u);
    if (buffer == NULL) {
        fprintf(stderr, "%s: error: cannot allocate input buffer\n", path);
        (void)fclose(input);
        return 0;
    }
    count = fread(buffer, 1u, SPRIG_MAX_SOURCE + 1u, input);
    if (ferror(input)) {
        fprintf(stderr, "%s: error: cannot read input\n", path);
        free(buffer);
        (void)fclose(input);
        return 0;
    }
    if (count > SPRIG_MAX_SOURCE) {
        fprintf(stderr, "%s: error: source exceeds 1 MiB\n", path);
        free(buffer);
        (void)fclose(input);
        return 0;
    }
    if (fclose(input) != 0) {
        fprintf(stderr, "%s: error: cannot close input\n", path);
        free(buffer);
        return 0;
    }
    buffer[count] = 0u;
    *source = buffer;
    *length = count;
    return 1;
}

static void print_diagnostic(const char *path, const Diagnostic *diagnostic) {
    fprintf(stderr, "%s:%zu:%zu: error: %s\n", path,
            diagnostic->line, diagnostic->column, diagnostic->message);
}

static int report_output_error(const char *path, const char *description) {
    fprintf(stderr, "%s:1:1: error: failed to write %s\n",
            path, description);
    return EXIT_IO_ERROR;
}

static int print_tokens(const char *path, const unsigned char *source,
                        size_t length) {
    Lexer lexer;
    Token token;

    /* Validate the complete stream before making token output observable. */
    lexer_init(&lexer, source, length);
    for (;;) {
        if (!lexer_next(&lexer, &token)) {
            fprintf(stderr, "%s:%zu:%zu: error: %s\n", path,
                    lexer.error_line, lexer.error_column, lexer.error);
            return EXIT_COMPILE_ERROR;
        }
        if (token.kind == TOK_EOF) {
            break;
        }
    }

    lexer_init(&lexer, source, length);
    for (;;) {
        if (!lexer_next(&lexer, &token)) {
            fprintf(stderr, "%s:%zu:%zu: error: %s\n", path,
                    lexer.error_line, lexer.error_column, lexer.error);
            return EXIT_COMPILE_ERROR;
        }
        if (printf("%zu:%zu %s", token.line, token.column,
                   token_kind_name(token.kind)) < 0) {
            return report_output_error(path, "token output");
        }
        if (token.kind == TOK_INTEGER) {
            if (printf(" %" PRId64, token.integer) < 0) {
                return report_output_error(path, "token output");
            }
        } else if (token.kind == TOK_IDENTIFIER) {
            if (printf(" %s", token.lexeme) < 0) {
                return report_output_error(path, "token output");
            }
        }
        if (putchar('\n') == EOF) {
            return report_output_error(path, "token output");
        }
        if (token.kind == TOK_EOF) {
            break;
        }
    }
    if (fflush(stdout) != 0 || ferror(stdout)) {
        return report_output_error(path, "token output");
    }
    return 0;
}

static void usage(const char *program) {
    fprintf(stderr,
            "usage: %s [--tokens|--disassemble] FILE\n", program);
}

int main(int argc, char **argv) {
    enum { MODE_RUN, MODE_TOKENS, MODE_DISASSEMBLE } mode = MODE_RUN;
    const char *path;
    unsigned char *source;
    size_t length;
    Program program;
    Diagnostic diagnostic;
    int result;

#ifdef SIGPIPE
    (void)signal(SIGPIPE, SIG_IGN);
#endif

    if (argc == 2) {
        path = argv[1];
    } else if (argc == 3 && strcmp(argv[1], "--tokens") == 0) {
        mode = MODE_TOKENS;
        path = argv[2];
    } else if (argc == 3 && strcmp(argv[1], "--disassemble") == 0) {
        mode = MODE_DISASSEMBLE;
        path = argv[2];
    } else {
        usage(argv[0]);
        return EXIT_USAGE_ERROR;
    }

    if (!read_source(path, &source, &length)) {
        return EXIT_IO_ERROR;
    }
    if (mode == MODE_TOKENS) {
        result = print_tokens(path, source, length);
        free(source);
        return result;
    }
    if (!compile_source(source, length, &program, &diagnostic)) {
        print_diagnostic(path, &diagnostic);
        free(source);
        return EXIT_COMPILE_ERROR;
    }
    free(source);
    if (mode == MODE_DISASSEMBLE) {
        disassemble_program(&program, stdout);
        if (fflush(stdout) != 0 || ferror(stdout)) {
            return report_output_error(path, "disassembly output");
        }
        return 0;
    }
    if (!vm_execute(&program, stdout, &diagnostic)) {
        if (fflush(stdout) != 0 || ferror(stdout)) {
            return report_output_error(path, "program output");
        }
        print_diagnostic(path, &diagnostic);
        return EXIT_RUNTIME_ERROR;
    }
    return 0;
}
