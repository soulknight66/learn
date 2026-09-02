package org.learningfactory.mica;

import java.util.List;

public final class Parser {
    private final List<Token> tokens;

    public Parser(List<Token> tokens) {
        this.tokens = tokens == null ? null : List.copyOf(tokens);
    }

    public List<Stmt> parse() {
        // TODO(student): implement the grammar in REQUIREMENTS.md using recursive descent.
        int tokenCount = tokens == null ? 0 : tokens.size();
        throw new UnsupportedOperationException("TODO(student): Parser.parse for " + tokenCount + " tokens");
    }
}
