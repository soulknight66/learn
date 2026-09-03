#include "sprig.h"

#include <stdio.h>
#include <string.h>

/* Milestone 4: replace this stub with checked stack-machine execution. */
int vm_execute(const Program *program, FILE *output, Diagnostic *diagnostic) {
    const Instruction *instruction;
    (void)output;
    memset(diagnostic, 0, sizeof(*diagnostic));
    if (program->count == 1u && program->code[0].opcode == OP_HALT) {
        return 1;
    }
    instruction = program->count == 0u ? NULL : &program->code[0];
    diagnostic->line = instruction == NULL ? 1u : instruction->line;
    diagnostic->column = instruction == NULL ? 1u : instruction->column;
    (void)snprintf(diagnostic->message, sizeof(diagnostic->message),
                   "virtual machine stage is not implemented");
    return 0;
}
