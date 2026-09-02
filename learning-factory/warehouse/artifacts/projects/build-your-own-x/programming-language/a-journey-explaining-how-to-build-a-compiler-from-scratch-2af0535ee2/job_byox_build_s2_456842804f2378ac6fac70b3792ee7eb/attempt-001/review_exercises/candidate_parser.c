#include <string.h>

/* Intentionally incomplete and unsafe review specimen. */
struct CandidateBinding {
    char name[32];
    int slot;
};

struct CandidateParser {
    struct CandidateBinding bindings[64];
    int binding_count;
    const char *identifier;
};

extern int candidate_parse_expression(struct CandidateParser *parser);
extern int candidate_emit_store(struct CandidateParser *parser, int slot);

int candidate_parse_let(struct CandidateParser *parser) {
    int slot = parser->binding_count++;
    strcpy(parser->bindings[slot].name, parser->identifier);
    parser->bindings[slot].slot = slot;
    (void)candidate_parse_expression(parser);
    (void)candidate_emit_store(parser, slot);
    return 1;
}
