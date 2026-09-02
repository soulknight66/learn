#include "sprig.h"

#include <stdio.h>
#include <string.h>

static int failures = 0;
static const char *const output_path = "build/vm_safety_output.tmp";

static FILE *open_output(void) {
    return fopen(output_path, "w+b");
}

static Instruction instruction(OpCode opcode, int64_t operand) {
    Instruction value;
    value.opcode = opcode;
    value.operand = operand;
    value.line = 3u;
    value.column = 4u;
    return value;
}

static void expect_failure(const char *name, Program *program,
                           const char *fragment) {
    Diagnostic diagnostic;
    FILE *output = open_output();
    int result;

    if (output == NULL) {
        fprintf(stderr, "FAIL %s: tmpfile unavailable\n", name);
        failures++;
        return;
    }
    result = vm_execute(program, output, &diagnostic);
    (void)fclose(output);
    (void)remove(output_path);
    if (result || strstr(diagnostic.message, fragment) == NULL ||
        diagnostic.line == 0u || diagnostic.column == 0u) {
        fprintf(stderr, "FAIL %s: result=%d diagnostic=%s\n",
                name, result, diagnostic.message);
        failures++;
    }
}

static void malformed_program_tests(void) {
    Program program;

    memset(&program, 0, sizeof(program));
    expect_failure("empty metadata", &program, "metadata");

    memset(&program, 0, sizeof(program));
    program.code[0] = instruction(OP_PRINT, 0);
    program.code[1] = instruction(OP_HALT, 0);
    program.count = 2u;
    expect_failure("print underflow", &program, "underflow");

    memset(&program, 0, sizeof(program));
    program.code[0] = instruction(OP_CONST, 1);
    program.code[1] = instruction(OP_HALT, 0);
    program.count = 2u;
    expect_failure("dirty halt", &program, "non-empty");

    memset(&program, 0, sizeof(program));
    program.code[0] = instruction(OP_LOAD, 0);
    program.code[1] = instruction(OP_HALT, 0);
    program.count = 2u;
    program.variable_count = 1u;
    expect_failure("uninitialized load", &program, "uninitialized");

    memset(&program, 0, sizeof(program));
    program.code[0] = instruction(OP_CONST, 1);
    program.code[1] = instruction(OP_STORE, 0);
    program.code[2] = instruction(OP_CONST, 2);
    program.code[3] = instruction(OP_STORE, 0);
    program.code[4] = instruction(OP_HALT, 0);
    program.count = 5u;
    program.variable_count = 1u;
    expect_failure("second store", &program, "initialized slot");

    memset(&program, 0, sizeof(program));
    program.code[0] = instruction(OP_LOAD, 1);
    program.code[1] = instruction(OP_HALT, 0);
    program.count = 2u;
    program.variable_count = 1u;
    expect_failure("bad slot", &program, "invalid variable slot");

    memset(&program, 0, sizeof(program));
    program.code[0] = instruction(OP_HALT, 0);
    program.code[1] = instruction(OP_HALT, 0);
    program.count = 2u;
    expect_failure("early halt", &program, "follow HALT");

    memset(&program, 0, sizeof(program));
    program.code[0] = instruction(OP_CONST, 1);
    program.count = 1u;
    expect_failure("missing halt", &program, "no HALT");

    memset(&program, 0, sizeof(program));
    program.code[0] = instruction((OpCode)999, 0);
    program.code[1] = instruction(OP_HALT, 0);
    program.count = 2u;
    expect_failure("unknown opcode", &program, "unknown opcode");
}

static void valid_program_test(void) {
    Program program;
    Diagnostic diagnostic;
    FILE *output;
    char buffer[32];
    size_t count;

    memset(&program, 0, sizeof(program));
    program.code[0] = instruction(OP_CONST, 42);
    program.code[1] = instruction(OP_PRINT, 0);
    program.code[2] = instruction(OP_HALT, 0);
    program.count = 3u;
    output = open_output();
    if (output == NULL || !vm_execute(&program, output, &diagnostic)) {
        fprintf(stderr, "FAIL valid bytecode\n");
        failures++;
        if (output != NULL) {
            (void)fclose(output);
        }
        (void)remove(output_path);
        return;
    }
    rewind(output);
    count = fread(buffer, 1u, sizeof(buffer) - 1u, output);
    buffer[count] = '\0';
    (void)fclose(output);
    (void)remove(output_path);
    if (strcmp(buffer, "42\n") != 0) {
        fprintf(stderr, "FAIL valid output: %s\n", buffer);
        failures++;
    }
}

int main(void) {
    malformed_program_tests();
    valid_program_test();
    if (failures != 0) {
        fprintf(stderr, "%d VM safety test(s) failed\n", failures);
        return 1;
    }
    puts("10 VM safety tests passed");
    return 0;
}
