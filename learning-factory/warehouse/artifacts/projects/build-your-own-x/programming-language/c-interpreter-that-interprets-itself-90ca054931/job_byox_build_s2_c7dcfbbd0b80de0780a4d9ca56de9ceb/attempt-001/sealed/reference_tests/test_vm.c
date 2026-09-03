#include "ember.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

static EmberProgram *make_program(const int64_t *words, size_t count,
                                  size_t local_count) {
    EmberProgram *program = calloc(1U, sizeof(*program));
    size_t index;
    if (program == NULL) {
        fprintf(stderr, "allocation failure\n");
        exit(2);
    }
    for (index = 0U; index < count; index++) {
        program->words[index] = words[index];
        program->lines[index] = 1U;
        program->columns[index] = (uint32_t)(index + 1U);
    }
    program->count = count;
    program->local_count = local_count;
    return program;
}

static void expect_failure(const char *name, const int64_t *words,
                           size_t count, size_t locals, uint64_t steps,
                           const char *fragment) {
    EmberProgram *program = make_program(words, count, locals);
    char error[512] = {0};
    int64_t result = 0;
    int status;
    status = ember_execute(program, NULL, 0U, steps, stdout, &result, error,
                           sizeof(error));
    if (status == 0 || strstr(error, fragment) == NULL) {
        fprintf(stderr, "FAIL %s: status=%d diagnostic=%s\n", name, status,
                error);
        failures++;
    }
    free(program);
}

static void expect_success(void) {
    static const int64_t words[] = {
        OP_PUSH, 6, OP_PUSH, 7, OP_MUL, OP_RETURN,
    };
    EmberProgram *program =
        make_program(words, sizeof(words) / sizeof(words[0]), 0U);
    char error[512] = {0};
    int64_t result = 0;
    int status;
    status = ember_execute(program, NULL, 0U, 20U, stdout, &result, error,
                           sizeof(error));
    if (status != 0 || result != 42) {
        fprintf(stderr,
                "FAIL successful arithmetic: status=%d result=%" PRId64
                " diagnostic=%s\n",
                status, result, error);
        failures++;
    }
    free(program);
}

int main(void) {
    static const int64_t invalid_opcode[] = {99};
    static const int64_t missing_operand[] = {OP_PUSH};
    static const int64_t underflow[] = {OP_ADD};
    static const int64_t bad_jump[] = {OP_JMP, 2};
    static const int64_t bad_local[] = {OP_LOAD_LOCAL, 0};
    static const int64_t bad_heap[] = {OP_PUSH, 4096, OP_HLOAD};
    static const int64_t overflow[] = {
        OP_PUSH, INT64_MAX, OP_PUSH, 1, OP_ADD, OP_RETURN,
    };
    static const int64_t budget[] = {OP_JMP, 0};
    static const int64_t negative_arg[] = {OP_PUSH, -1, OP_ARG, OP_RETURN};

    expect_success();
    expect_failure("invalid opcode", invalid_opcode, 1U, 0U, 10U,
                   "invalid opcode");
    expect_failure("missing operand", missing_operand, 1U, 0U, 10U,
                   "missing its operand");
    expect_failure("stack underflow", underflow, 1U, 0U, 10U,
                   "stack underflow");
    expect_failure("jump target", bad_jump, 2U, 0U, 10U,
                   "invalid jump target");
    expect_failure("local slot", bad_local, 2U, 0U, 10U,
                   "invalid local slot");
    expect_failure("heap index", bad_heap, 3U, 0U, 10U,
                   "invalid heap index");
    expect_failure("overflow", overflow, 6U, 0U, 10U, "overflow");
    expect_failure("budget", budget, 2U, 0U, 3U, "budget exceeded");
    expect_failure("negative arg", negative_arg, 4U, 0U, 10U,
                   "negative argument index");

    if (failures != 0) {
        fprintf(stderr, "%d VM unit test(s) failed\n", failures);
        return 1;
    }
    printf("VM unit tests: 10 passed\n");
    return 0;
}
