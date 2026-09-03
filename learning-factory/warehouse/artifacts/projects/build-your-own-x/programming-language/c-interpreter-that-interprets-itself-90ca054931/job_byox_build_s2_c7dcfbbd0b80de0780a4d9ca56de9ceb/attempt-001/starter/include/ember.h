#ifndef EMBER_H
#define EMBER_H

#include <stddef.h>
#include <stdint.h>

#define EMBER_IDENT_MAX 63U
#define EMBER_CODE_MAX 65536U
#define EMBER_LOCAL_MAX 256U
#define EMBER_STACK_MAX 4096U
#define EMBER_HEAP_MAX 4096U
#define EMBER_DEFAULT_STEPS 1000000ULL

typedef enum {
    TOK_EOF = 0,
    TOK_ERROR,
    TOK_INTEGER,
    TOK_IDENTIFIER,
    TOK_INT,
    TOK_MAIN,
    TOK_IF,
    TOK_ELSE,
    TOK_WHILE,
    TOK_RETURN,
    TOK_PRINT,
    TOK_ARG,
    TOK_LOAD,
    TOK_STORE,
    TOK_LPAREN,
    TOK_RPAREN,
    TOK_LBRACE,
    TOK_RBRACE,
    TOK_SEMICOLON,
    TOK_COMMA,
    TOK_ASSIGN,
    TOK_PLUS,
    TOK_MINUS,
    TOK_STAR,
    TOK_SLASH,
    TOK_PERCENT,
    TOK_BANG,
    TOK_EQ,
    TOK_NE,
    TOK_LT,
    TOK_LE,
    TOK_GT,
    TOK_GE,
    TOK_AND,
    TOK_OR
} TokenKind;

typedef struct {
    TokenKind kind;
    const char *start;
    size_t length;
    size_t line;
    size_t column;
    int64_t integer;
    const char *message;
} Token;

typedef struct {
    const char *source;
    size_t length;
    size_t offset;
    size_t line;
    size_t column;
} Lexer;

typedef enum {
    OP_HALT = 0,
    OP_PUSH = 1,
    OP_LOAD_LOCAL = 2,
    OP_STORE_LOCAL = 3,
    OP_ADD = 4,
    OP_SUB = 5,
    OP_MUL = 6,
    OP_DIV = 7,
    OP_MOD = 8,
    OP_EQ = 9,
    OP_NE = 10,
    OP_LT = 11,
    OP_LE = 12,
    OP_GT = 13,
    OP_GE = 14,
    OP_NEG = 15,
    OP_NOT = 16,
    OP_JMP = 17,
    OP_JZ = 18,
    OP_PRINT = 19,
    OP_ARG = 20,
    OP_HLOAD = 21,
    OP_HSTORE = 22,
    OP_POP = 23,
    OP_RETURN = 24
} OpCode;

typedef struct {
    int64_t words[EMBER_CODE_MAX];
    size_t count;
} Bytecode;

void lexer_init(Lexer *lexer, const char *source, size_t length);
Token lexer_next(Lexer *lexer);
const char *token_kind_name(TokenKind kind);

/* Returns zero on success and writes a human-readable message on failure. */
int ember_compile(const char *path, const char *source, size_t length,
                  Bytecode *output, char *error, size_t error_size);

/* Executes verified or untrusted bytecode subject to the supplied step limit. */
int ember_execute(const Bytecode *code, const int64_t *arguments,
                  size_t argument_count, uint64_t max_steps,
                  int64_t *return_value, char *error, size_t error_size);

#endif
