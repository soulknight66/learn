#ifndef SEALED_EMBER_H
#define SEALED_EMBER_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define EMBER_SOURCE_MAX 1048576U
#define EMBER_IDENT_MAX 63U
#define EMBER_CODE_MAX 65536U
#define EMBER_LOCAL_MAX 256U
#define EMBER_STACK_MAX 4096U
#define EMBER_HEAP_MAX 4096U
#define EMBER_DEFAULT_STEPS 1000000ULL

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
    uint32_t lines[EMBER_CODE_MAX];
    uint32_t columns[EMBER_CODE_MAX];
    size_t count;
    size_t local_count;
} EmberProgram;

int ember_compile(const char *path, const char *source, size_t length,
                  EmberProgram *program, char *error, size_t error_size);
int ember_dump_tokens(const char *path, const char *source, size_t length,
                      FILE *output, char *error, size_t error_size);
int ember_execute(const EmberProgram *program, const int64_t *arguments,
                  size_t argument_count, uint64_t max_steps, FILE *output,
                  int64_t *return_value, char *error, size_t error_size);

#endif
