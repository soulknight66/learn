/* Deliberately flawed pseudocode-like C used only for review. */
static void resolve_declaration(struct resolver *resolver,
                                struct declaration *declaration) {
    declaration->slot = resolver->count;
    resolver->symbols[resolver->count].name = declaration->name;
    resolver->count++;
    resolve_expression(resolver, declaration->initializer);
}
