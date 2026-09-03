#include "ember.h"

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;
static int checks = 0;

static EmberProgram *make_program(const int64_t *words, size_t count,
                                  size_t local_count) {
    EmberProgram *program = calloc(1U, sizeof(*program));
    size_t index;
    if (program == NULL) {
        fprintf(stderr, "allocation failure\n");
        exit(2);
    }
    if (count > EMBER_CODE_MAX) {
        fprintf(stderr, "test program exceeds code capacity\n");
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
                           size_t site, const char *fragment) {
    EmberProgram *program = make_program(words, count, locals);
    char error[512] = {0};
    char prefix[128];
    int64_t result = 0;
    int status;
    (void)snprintf(prefix, sizeof(prefix),
                   "direct-vm.ec:1:%zu: runtime error: ", site + 1U);
    checks++;
    status = ember_execute("direct-vm.ec", program, NULL, 0U, steps, stdout,
                           &result, error, sizeof(error));
    if (status == 0 || strncmp(error, prefix, strlen(prefix)) != 0 ||
        strstr(error, fragment) == NULL) {
        fprintf(stderr, "FAIL %s: status=%d diagnostic=%s\n", name, status,
                error);
        failures++;
    }
    free(program);
}

static void expect_invalid_metadata(const char *name, size_t count,
                                    size_t locals, const char *prefix) {
    static const int64_t halt[] = {OP_HALT};
    EmberProgram *program = make_program(halt, count, locals);
    char error[512] = {0};
    int64_t result = 0;
    int status;
    checks++;
    status = ember_execute("direct-vm.ec", program, NULL, 0U, 1U, stdout,
                           &result, error, sizeof(error));
    if (status == 0 || strncmp(error, prefix, strlen(prefix)) != 0 ||
        strstr(error, "invalid program metadata") == NULL) {
        fprintf(stderr, "FAIL %s: status=%d diagnostic=%s\n", name, status,
                error);
        failures++;
    }
    free(program);
}

static void expect_stack_overflow(void) {
    const size_t pushes = EMBER_STACK_MAX + 1U;
    const size_t count = pushes * 2U + 1U;
    int64_t *words = calloc(count, sizeof(*words));
    size_t index;
    if (words == NULL) {
        fprintf(stderr, "allocation failure\n");
        exit(2);
    }
    for (index = 0U; index < pushes; index++) {
        words[index * 2U] = OP_PUSH;
        words[index * 2U + 1U] = 0;
    }
    words[count - 1U] = OP_HALT;
    expect_failure("stack overflow", words, count, 0U, 10000U,
                   EMBER_STACK_MAX * 2U, "stack overflow");
    free(words);
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
    checks++;
    status = ember_execute("direct-vm.ec", program, NULL, 0U, 20U, stdout,
                           &result, error, sizeof(error));
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
    static const int64_t escaped_pc[] = {OP_PUSH, 1};
    static const int64_t underflow[] = {OP_ADD};
    static const int64_t pop_underflow[] = {OP_POP};
    static const int64_t bad_jump_equal[] = {OP_JMP, 2};
    static const int64_t bad_jump_negative[] = {OP_JMP, -1};
    static const int64_t bad_local_load[] = {OP_LOAD_LOCAL, 0};
    static const int64_t bad_local_store[] = {OP_STORE_LOCAL, 0};
    static const int64_t bad_heap_load[] = {OP_PUSH, 4096, OP_HLOAD};
    static const int64_t bad_heap_store[] = {
        OP_PUSH, -1, OP_PUSH, 0, OP_HSTORE,
    };
    static const int64_t add_overflow[] = {
        OP_PUSH, INT64_MAX, OP_PUSH, 1, OP_ADD, OP_RETURN,
    };
    static const int64_t subtract_overflow[] = {
        OP_PUSH, INT64_MIN, OP_PUSH, 1, OP_SUB, OP_RETURN,
    };
    static const int64_t multiply_overflow[] = {
        OP_PUSH, INT64_MAX, OP_PUSH, 2, OP_MUL, OP_RETURN,
    };
    static const int64_t division_zero[] = {
        OP_PUSH, 1, OP_PUSH, 0, OP_DIV, OP_RETURN,
    };
    static const int64_t remainder_zero[] = {
        OP_PUSH, 1, OP_PUSH, 0, OP_MOD, OP_RETURN,
    };
    static const int64_t division_overflow[] = {
        OP_PUSH, INT64_MIN, OP_PUSH, -1, OP_DIV, OP_RETURN,
    };
    static const int64_t remainder_overflow[] = {
        OP_PUSH, INT64_MIN, OP_PUSH, -1, OP_MOD, OP_RETURN,
    };
    static const int64_t negate_overflow[] = {
        OP_PUSH, INT64_MIN, OP_NEG, OP_RETURN,
    };
    static const int64_t budget[] = {OP_JMP, 0};
    static const int64_t negative_arg[] = {OP_PUSH, -1, OP_ARG, OP_RETURN};

    expect_success();
    expect_failure("invalid opcode", invalid_opcode, 1U, 0U, 10U,
                   0U, "invalid opcode");
    expect_failure("missing operand", missing_operand, 1U, 0U, 10U,
                   0U, "missing its operand");
    expect_failure("escaped program counter", escaped_pc, 2U, 0U, 10U,
                   0U, "program counter escaped");
    expect_failure("stack underflow", underflow, 1U, 0U, 10U,
                   0U, "stack underflow");
    expect_failure("pop underflow", pop_underflow, 1U, 0U, 10U,
                   0U, "stack underflow");
    expect_stack_overflow();
    expect_failure("jump target equal to count", bad_jump_equal, 2U, 0U,
                   10U, 0U, "invalid jump target");
    expect_failure("negative jump target", bad_jump_negative, 2U, 0U, 10U,
                   0U, "invalid jump target");
    expect_failure("load local slot", bad_local_load, 2U, 0U, 10U,
                   0U, "invalid local slot");
    expect_failure("store local slot", bad_local_store, 2U, 0U, 10U,
                   0U, "invalid local slot");
    expect_failure("load heap index", bad_heap_load, 3U, 0U, 10U,
                   2U, "invalid heap index");
    expect_failure("store heap index", bad_heap_store, 5U, 0U, 10U,
                   4U, "invalid heap index");
    expect_failure("addition overflow", add_overflow, 6U, 0U, 10U,
                   4U, "signed arithmetic overflow");
    expect_failure("subtraction overflow", subtract_overflow, 6U, 0U, 10U,
                   4U, "signed arithmetic overflow");
    expect_failure("multiplication overflow", multiply_overflow, 6U, 0U,
                   10U, 4U, "signed arithmetic overflow");
    expect_failure("division by zero", division_zero, 6U, 0U, 10U,
                   4U, "division by zero");
    expect_failure("remainder by zero", remainder_zero, 6U, 0U, 10U,
                   4U, "remainder by zero");
    expect_failure("division overflow", division_overflow, 6U, 0U, 10U,
                   4U, "signed arithmetic overflow");
    expect_failure("remainder overflow", remainder_overflow, 6U, 0U, 10U,
                   4U, "signed arithmetic overflow");
    expect_failure("negation overflow", negate_overflow, 4U, 0U, 10U,
                   2U, "signed arithmetic overflow");
    expect_failure("budget", budget, 2U, 0U, 3U, 0U, "budget exceeded");
    expect_failure("zero budget", budget, 2U, 0U, 0U, 0U,
                   "budget exceeded");
    expect_failure("negative arg", negative_arg, 4U, 0U, 10U,
                   2U, "negative argument index");
    expect_invalid_metadata(
        "empty program", 0U, 0U,
        "direct-vm.ec:0:0: runtime error: ");
    expect_invalid_metadata(
        "local metadata", 1U, EMBER_LOCAL_MAX + 1U,
        "direct-vm.ec:1:1: runtime error: ");

    if (failures != 0) {
        fprintf(stderr, "%d VM unit test(s) failed\n", failures);
        return 1;
    }
    printf("VM unit tests: %d passed\n", checks);
    return 0;
}
