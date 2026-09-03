#include "sprig.h"

#include <inttypes.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

static int runtime_error(Diagnostic *diagnostic,
                         const Instruction *instruction,
                         const char *message) {
    diagnostic->line = instruction == NULL ? 1u : instruction->line;
    diagnostic->column = instruction == NULL ? 1u : instruction->column;
    (void)snprintf(diagnostic->message, sizeof(diagnostic->message),
                   "%s", message);
    return 0;
}

static int checked_add(int64_t left, int64_t right, int64_t *result) {
    if ((right > 0 && left > INT64_MAX - right) ||
        (right < 0 && left < INT64_MIN - right)) {
        return 0;
    }
    *result = left + right;
    return 1;
}

static int checked_sub(int64_t left, int64_t right, int64_t *result) {
    if ((right > 0 && left < INT64_MIN + right) ||
        (right < 0 && left > INT64_MAX + right)) {
        return 0;
    }
    *result = left - right;
    return 1;
}

static int checked_mul(int64_t left, int64_t right, int64_t *result) {
    if (left == 0 || right == 0) {
        *result = 0;
        return 1;
    }
    if (left > 0) {
        if ((right > 0 && left > INT64_MAX / right) ||
            (right < 0 && right < INT64_MIN / left)) {
            return 0;
        }
    } else {
        if ((right > 0 && left < INT64_MIN / right) ||
            (right < 0 && left < INT64_MAX / right)) {
            return 0;
        }
    }
    *result = left * right;
    return 1;
}

static int checked_binary(OpCode opcode, int64_t left, int64_t right,
                          int64_t *result, const char **error) {
    switch (opcode) {
        case OP_ADD:
            if (!checked_add(left, right, result)) {
                *error = "integer overflow in addition";
                return 0;
            }
            return 1;
        case OP_SUB:
            if (!checked_sub(left, right, result)) {
                *error = "integer overflow in subtraction";
                return 0;
            }
            return 1;
        case OP_MUL:
            if (!checked_mul(left, right, result)) {
                *error = "integer overflow in multiplication";
                return 0;
            }
            return 1;
        case OP_DIV:
            if (right == 0) {
                *error = "division by zero";
                return 0;
            }
            if (left == INT64_MIN && right == -1) {
                *error = "integer overflow in division";
                return 0;
            }
            *result = left / right;
            return 1;
        default:
            *error = "invalid binary opcode";
            return 0;
    }
}

int vm_execute(const Program *program, FILE *output, Diagnostic *diagnostic) {
    int64_t stack[SPRIG_MAX_STACK];
    int64_t variables[SPRIG_MAX_VARIABLES];
    unsigned char initialized[SPRIG_MAX_VARIABLES];
    size_t stack_count = 0u;
    size_t pc;

    memset(diagnostic, 0, sizeof(*diagnostic));
    memset(variables, 0, sizeof(variables));
    memset(initialized, 0, sizeof(initialized));
    if (program->count == 0u ||
        program->count > SPRIG_MAX_INSTRUCTIONS ||
        program->variable_count > SPRIG_MAX_VARIABLES) {
        return runtime_error(diagnostic, NULL, "invalid program metadata");
    }

    for (pc = 0u; pc < program->count; pc++) {
        const Instruction *instruction = &program->code[pc];
        int64_t left;
        int64_t right;
        int64_t result;
        const char *arithmetic_error = NULL;
        size_t slot;

        switch (instruction->opcode) {
            case OP_CONST:
                if (stack_count >= SPRIG_MAX_STACK) {
                    return runtime_error(diagnostic, instruction,
                                         "value stack overflow");
                }
                stack[stack_count++] = instruction->operand;
                break;
            case OP_LOAD:
                if (instruction->operand < 0 ||
                    (uint64_t)instruction->operand >= program->variable_count) {
                    return runtime_error(diagnostic, instruction,
                                         "invalid variable slot in LOAD");
                }
                slot = (size_t)instruction->operand;
                if (!initialized[slot]) {
                    return runtime_error(diagnostic, instruction,
                                         "LOAD from uninitialized slot");
                }
                if (stack_count >= SPRIG_MAX_STACK) {
                    return runtime_error(diagnostic, instruction,
                                         "value stack overflow");
                }
                stack[stack_count++] = variables[slot];
                break;
            case OP_STORE:
                if (instruction->operand < 0 ||
                    (uint64_t)instruction->operand >= program->variable_count) {
                    return runtime_error(diagnostic, instruction,
                                         "invalid variable slot in STORE");
                }
                if (stack_count == 0u) {
                    return runtime_error(diagnostic, instruction,
                                         "value stack underflow in STORE");
                }
                slot = (size_t)instruction->operand;
                if (initialized[slot]) {
                    return runtime_error(diagnostic, instruction,
                                         "STORE to initialized slot");
                }
                variables[slot] = stack[--stack_count];
                initialized[slot] = 1u;
                break;
            case OP_ADD:
            case OP_SUB:
            case OP_MUL:
            case OP_DIV:
                if (stack_count < 2u) {
                    return runtime_error(diagnostic, instruction,
                                         "value stack underflow in arithmetic");
                }
                right = stack[--stack_count];
                left = stack[--stack_count];
                if (!checked_binary(instruction->opcode, left, right,
                                    &result, &arithmetic_error)) {
                    return runtime_error(diagnostic, instruction,
                                         arithmetic_error);
                }
                stack[stack_count++] = result;
                break;
            case OP_NEG:
                if (stack_count == 0u) {
                    return runtime_error(diagnostic, instruction,
                                         "value stack underflow in NEG");
                }
                if (stack[stack_count - 1u] == INT64_MIN) {
                    return runtime_error(diagnostic, instruction,
                                         "integer overflow in negation");
                }
                stack[stack_count - 1u] = -stack[stack_count - 1u];
                break;
            case OP_PRINT:
                if (stack_count == 0u) {
                    return runtime_error(diagnostic, instruction,
                                         "value stack underflow in PRINT");
                }
                if (fprintf(output, "%" PRId64 "\n",
                            stack[--stack_count]) < 0) {
                    return runtime_error(diagnostic, instruction,
                                         "failed to write program output");
                }
                break;
            case OP_HALT:
                if (pc + 1u != program->count) {
                    return runtime_error(diagnostic, instruction,
                                         "instructions follow HALT");
                }
                if (stack_count != 0u) {
                    return runtime_error(diagnostic, instruction,
                                         "HALT with non-empty value stack");
                }
                if (fflush(output) != 0) {
                    return runtime_error(diagnostic, instruction,
                                         "failed to flush program output");
                }
                return 1;
            default:
                return runtime_error(diagnostic, instruction,
                                     "unknown opcode");
        }
    }
    return runtime_error(diagnostic, &program->code[program->count - 1u],
                         "program has no HALT instruction");
}
