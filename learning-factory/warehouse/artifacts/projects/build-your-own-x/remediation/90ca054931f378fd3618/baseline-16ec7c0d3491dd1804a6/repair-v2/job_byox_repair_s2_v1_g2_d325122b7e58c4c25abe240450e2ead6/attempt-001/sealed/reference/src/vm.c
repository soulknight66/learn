#include "ember.h"

#include <inttypes.h>
#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    const char *source_path;
    const EmberProgram *program;
    const int64_t *arguments;
    size_t argument_count;
    uint64_t max_steps;
    uint64_t steps;
    size_t pc;
    int64_t locals[EMBER_LOCAL_MAX];
    int64_t stack[EMBER_STACK_MAX];
    size_t stack_count;
    int64_t heap[EMBER_HEAP_MAX];
    FILE *output;
    char *error;
    size_t error_size;
    size_t instruction_site;
    int failed;
} Vm;

static void runtime_fail(Vm *vm, const char *format, ...) {
    char detail[256];
    const char *path;
    uint32_t line = 0U;
    uint32_t column = 0U;
    va_list arguments;
    if (vm->failed) {
        return;
    }
    if (vm->instruction_site < vm->program->count) {
        line = vm->program->lines[vm->instruction_site];
        column = vm->program->columns[vm->instruction_site];
    }
    path = vm->source_path != NULL ? vm->source_path : "<bytecode>";
    va_start(arguments, format);
    (void)vsnprintf(detail, sizeof(detail), format, arguments);
    va_end(arguments);
    (void)snprintf(vm->error, vm->error_size,
                   "%s:%" PRIu32 ":%" PRIu32 ": runtime error: %s", path,
                   line, column, detail);
    vm->failed = 1;
}

static int push(Vm *vm, int64_t value) {
    if (vm->stack_count >= EMBER_STACK_MAX) {
        runtime_fail(vm, "operand stack overflow");
        return 0;
    }
    vm->stack[vm->stack_count++] = value;
    return 1;
}

static int pop(Vm *vm, int64_t *value) {
    if (vm->stack_count == 0U) {
        runtime_fail(vm, "operand stack underflow");
        return 0;
    }
    *value = vm->stack[--vm->stack_count];
    return 1;
}

static int operand(Vm *vm, int64_t *value) {
    if (vm->pc >= vm->program->count) {
        runtime_fail(vm, "instruction is missing its operand word");
        return 0;
    }
    *value = vm->program->words[vm->pc++];
    return 1;
}

static int valid_target(Vm *vm, int64_t target) {
    if (target < 0 || (uint64_t)target >= (uint64_t)vm->program->count) {
        runtime_fail(vm, "invalid jump target %" PRId64, target);
        return 0;
    }
    return 1;
}

static int binary_values(Vm *vm, int64_t *left, int64_t *right) {
    if (vm->stack_count < 2U) {
        runtime_fail(vm, "operand stack underflow");
        return 0;
    }
    *right = vm->stack[--vm->stack_count];
    *left = vm->stack[--vm->stack_count];
    return 1;
}

static void arithmetic(Vm *vm, OpCode op) {
    int64_t left;
    int64_t right;
    int64_t result = 0;
    int overflow = 0;
    if (!binary_values(vm, &left, &right)) {
        return;
    }
    switch (op) {
    case OP_ADD:
        overflow = __builtin_add_overflow(left, right, &result);
        break;
    case OP_SUB:
        overflow = __builtin_sub_overflow(left, right, &result);
        break;
    case OP_MUL:
        overflow = __builtin_mul_overflow(left, right, &result);
        break;
    case OP_DIV:
        if (right == 0) {
            runtime_fail(vm, "division by zero");
            return;
        }
        if (left == INT64_MIN && right == -1) {
            overflow = 1;
        } else {
            result = left / right;
        }
        break;
    case OP_MOD:
        if (right == 0) {
            runtime_fail(vm, "remainder by zero");
            return;
        }
        if (left == INT64_MIN && right == -1) {
            overflow = 1;
        } else {
            result = left % right;
        }
        break;
    default:
        runtime_fail(vm, "internal arithmetic dispatch error");
        return;
    }
    if (overflow) {
        runtime_fail(vm, "signed arithmetic overflow");
        return;
    }
    (void)push(vm, result);
}

static void comparison(Vm *vm, OpCode op) {
    int64_t left;
    int64_t right;
    int64_t result = 0;
    if (!binary_values(vm, &left, &right)) {
        return;
    }
    switch (op) {
    case OP_EQ:
        result = left == right;
        break;
    case OP_NE:
        result = left != right;
        break;
    case OP_LT:
        result = left < right;
        break;
    case OP_LE:
        result = left <= right;
        break;
    case OP_GT:
        result = left > right;
        break;
    case OP_GE:
        result = left >= right;
        break;
    default:
        runtime_fail(vm, "internal comparison dispatch error");
        return;
    }
    (void)push(vm, result);
}

int ember_execute(const char *source_path, const EmberProgram *program,
                  const int64_t *arguments, size_t argument_count,
                  uint64_t max_steps, FILE *output, int64_t *return_value,
                  char *error, size_t error_size) {
    Vm vm;
    memset(&vm, 0, sizeof(vm));
    vm.source_path = source_path;
    vm.program = program;
    vm.arguments = arguments;
    vm.argument_count = argument_count;
    vm.max_steps = max_steps;
    vm.output = output;
    vm.error = error;
    vm.error_size = error_size;

    if (program->count == 0U || program->count > EMBER_CODE_MAX ||
        program->local_count > EMBER_LOCAL_MAX) {
        runtime_fail(&vm, "invalid program metadata");
        return 1;
    }

    while (!vm.failed) {
        int64_t raw_op;
        OpCode op;
        int64_t value;
        int64_t extra;

        if (vm.pc >= program->count) {
            runtime_fail(&vm, "program counter escaped bytecode");
            break;
        }
        if (vm.steps >= vm.max_steps) {
            vm.instruction_site = vm.pc;
            runtime_fail(&vm, "instruction budget exceeded");
            break;
        }
        vm.steps++;
        vm.instruction_site = vm.pc;
        raw_op = program->words[vm.pc++];
        if (raw_op < OP_HALT || raw_op > OP_RETURN) {
            runtime_fail(&vm, "invalid opcode %" PRId64, raw_op);
            break;
        }
        op = (OpCode)raw_op;

        if (op >= OP_ADD && op <= OP_MOD) {
            arithmetic(&vm, op);
            continue;
        }
        if (op >= OP_EQ && op <= OP_GE) {
            comparison(&vm, op);
            continue;
        }

        switch (op) {
        case OP_HALT:
            if (return_value != NULL) {
                *return_value = 0;
            }
            return 0;
        case OP_PUSH:
            if (operand(&vm, &value)) {
                (void)push(&vm, value);
            }
            break;
        case OP_LOAD_LOCAL:
            if (operand(&vm, &value)) {
                if (value < 0 || (uint64_t)value >= program->local_count) {
                    runtime_fail(&vm, "invalid local slot %" PRId64, value);
                } else {
                    (void)push(&vm, vm.locals[(size_t)value]);
                }
            }
            break;
        case OP_STORE_LOCAL:
            if (operand(&vm, &value)) {
                if (value < 0 || (uint64_t)value >= program->local_count) {
                    runtime_fail(&vm, "invalid local slot %" PRId64, value);
                } else if (pop(&vm, &extra)) {
                    vm.locals[(size_t)value] = extra;
                }
            }
            break;
        case OP_NEG:
            if (pop(&vm, &value)) {
                if (value == INT64_MIN) {
                    runtime_fail(&vm, "signed arithmetic overflow");
                } else {
                    (void)push(&vm, -value);
                }
            }
            break;
        case OP_NOT:
            if (pop(&vm, &value)) {
                (void)push(&vm, value == 0);
            }
            break;
        case OP_JMP:
            if (operand(&vm, &value) && valid_target(&vm, value)) {
                vm.pc = (size_t)value;
            }
            break;
        case OP_JZ:
            if (operand(&vm, &value) && valid_target(&vm, value) &&
                pop(&vm, &extra) && extra == 0) {
                vm.pc = (size_t)value;
            }
            break;
        case OP_PRINT:
            if (pop(&vm, &value) &&
                fprintf(output, "%" PRId64 "\n", value) < 0) {
                runtime_fail(&vm, "output write failed");
            }
            break;
        case OP_ARG:
            if (pop(&vm, &value)) {
                if (value < 0) {
                    runtime_fail(&vm, "negative argument index");
                } else if ((uint64_t)value >= (uint64_t)argument_count) {
                    (void)push(&vm, 0);
                } else {
                    (void)push(&vm, arguments[(size_t)value]);
                }
            }
            break;
        case OP_HLOAD:
            if (pop(&vm, &value)) {
                if (value < 0 || (uint64_t)value >= EMBER_HEAP_MAX) {
                    runtime_fail(&vm, "invalid heap index %" PRId64, value);
                } else {
                    (void)push(&vm, vm.heap[(size_t)value]);
                }
            }
            break;
        case OP_HSTORE:
            if (binary_values(&vm, &value, &extra)) {
                if (value < 0 || (uint64_t)value >= EMBER_HEAP_MAX) {
                    runtime_fail(&vm, "invalid heap index %" PRId64, value);
                } else {
                    vm.heap[(size_t)value] = extra;
                }
            }
            break;
        case OP_POP:
            (void)pop(&vm, &value);
            break;
        case OP_RETURN:
            if (pop(&vm, &value)) {
                if (return_value != NULL) {
                    *return_value = value;
                }
                return 0;
            }
            break;
        case OP_ADD:
        case OP_SUB:
        case OP_MUL:
        case OP_DIV:
        case OP_MOD:
        case OP_EQ:
        case OP_NE:
        case OP_LT:
        case OP_LE:
        case OP_GT:
        case OP_GE:
            runtime_fail(&vm, "internal grouped dispatch error");
            break;
        }
    }
    return 1;
}
