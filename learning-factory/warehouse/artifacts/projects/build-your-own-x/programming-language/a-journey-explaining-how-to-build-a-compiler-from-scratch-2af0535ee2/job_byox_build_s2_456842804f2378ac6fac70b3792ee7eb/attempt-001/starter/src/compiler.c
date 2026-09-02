#include "sprig.h"

#include <stdio.h>
#include <string.h>

/*
 * Milestones 1--3 live here. Replace the deliberate stub with a one-token
 * lookahead recursive-descent parser. Emit an instruction only after all of
 * its operands have compiled successfully. See REQUIREMENTS.md for grammar.
 */
int compile_source(const unsigned char *source, size_t length,
                   Program *program, Diagnostic *diagnostic) {
    Lexer lexer;
    Token token;

    memset(program, 0, sizeof(*program));
    memset(diagnostic, 0, sizeof(*diagnostic));
    lexer_init(&lexer, source, length);
    if (!lexer_next(&lexer, &token)) {
        diagnostic->line = lexer.error_line;
        diagnostic->column = lexer.error_column;
        (void)snprintf(diagnostic->message, sizeof(diagnostic->message),
                       "%s", lexer.error);
        return 0;
    }
    if (token.kind != TOK_EOF) {
        diagnostic->line = token.line;
        diagnostic->column = token.column;
        (void)snprintf(diagnostic->message, sizeof(diagnostic->message),
                       "compiler stage is not implemented");
        return 0;
    }
    program->code[0].opcode = OP_HALT;
    program->code[0].line = token.line;
    program->code[0].column = token.column;
    program->count = 1u;
    return 1;
}

static const char *opcode_name(OpCode opcode) {
    static const char *const names[] = {
        "CONST", "LOAD", "STORE", "ADD", "SUB",
        "MUL", "DIV", "NEG", "PRINT", "HALT"
    };
    size_t index = (size_t)opcode;
    if (index >= sizeof(names) / sizeof(names[0])) {
        return "UNKNOWN";
    }
    return names[index];
}

void disassemble_program(const Program *program, FILE *output) {
    size_t index;
    for (index = 0u; index < program->count; index++) {
        const Instruction *instruction = &program->code[index];
        fprintf(output, "%04zu %-5s", index,
                opcode_name(instruction->opcode));
        if (instruction->opcode == OP_CONST ||
            instruction->opcode == OP_LOAD ||
            instruction->opcode == OP_STORE) {
            fprintf(output, " %lld", (long long)instruction->operand);
        }
        fprintf(output, " @ %zu:%zu\n",
                instruction->line, instruction->column);
    }
}
