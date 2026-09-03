#ifndef SPRIG_H
#define SPRIG_H

#include <stdint.h>
#include <stdio.h>
#include <stddef.h>

#define SPRIG_MAX_SOURCE (1024u * 1024u)
#define SPRIG_MAX_NAME 31u
#define SPRIG_MAX_VARIABLES 64u
#define SPRIG_MAX_INSTRUCTIONS 1024u
#define SPRIG_MAX_STACK 256u
#define SPRIG_MAX_NESTING 512u

typedef enum {
    TOK_EOF,
    TOK_INTEGER,
    TOK_IDENTIFIER,
    TOK_LET,
    TOK_PRINT,
    TOK_EQUAL,
    TOK_SEMICOLON,
    TOK_PLUS,
    TOK_MINUS,
    TOK_STAR,
    TOK_SLASH,
    TOK_LEFT_PAREN,
    TOK_RIGHT_PAREN
} TokenKind;

typedef struct {
    TokenKind kind;
    int64_t integer;
    char lexeme[SPRIG_MAX_NAME + 1u];
    size_t line;
    size_t column;
} Token;

typedef struct {
    const unsigned char *source;
    size_t length;
    size_t index;
    size_t line;
    size_t column;
    char error[160];
    size_t error_line;
    size_t error_column;
} Lexer;

typedef enum {
    OP_CONST,
    OP_LOAD,
    OP_STORE,
    OP_ADD,
    OP_SUB,
    OP_MUL,
    OP_DIV,
    OP_NEG,
    OP_PRINT,
    OP_HALT
} OpCode;

typedef struct {
    OpCode opcode;
    int64_t operand;
    size_t line;
    size_t column;
} Instruction;

typedef struct {
    Instruction code[SPRIG_MAX_INSTRUCTIONS];
    size_t count;
    size_t variable_count;
} Program;

typedef struct {
    char message[160];
    size_t line;
    size_t column;
} Diagnostic;

void lexer_init(Lexer *lexer, const unsigned char *source, size_t length);
int lexer_next(Lexer *lexer, Token *token);
const char *token_kind_name(TokenKind kind);

int compile_source(const unsigned char *source, size_t length,
                   Program *program, Diagnostic *diagnostic);
void disassemble_program(const Program *program, FILE *output);
int vm_execute(const Program *program, FILE *output, Diagnostic *diagnostic);

#endif
