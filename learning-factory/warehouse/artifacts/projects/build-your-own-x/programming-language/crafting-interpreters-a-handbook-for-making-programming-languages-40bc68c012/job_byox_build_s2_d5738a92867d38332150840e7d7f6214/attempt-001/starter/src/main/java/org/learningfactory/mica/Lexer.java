package org.learningfactory.mica;

import java.util.List;

public final class Lexer {
    private final String source;

    public Lexer(String source) {
        if (source == null) throw new MicaException(MicaException.Kind.LEX, 1, 1, "source must not be null");
        this.source = source;
    }

    public List<Token> scanTokens() {
        // TODO(student): scan source left-to-right, decode string escapes, and append a located EOF.
        throw new UnsupportedOperationException("TODO(student): Lexer.scanTokens for " + source.length() + " characters");
    }
}
