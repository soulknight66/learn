package org.learningfactory.mica;

import java.util.Objects;

public record Token(TokenType type, String lexeme, Object literal, int line, int column) {
    public Token {
        Objects.requireNonNull(type, "type");
        Objects.requireNonNull(lexeme, "lexeme");
        if (line < 1 || column < 1) {
            throw new IllegalArgumentException("token locations are one-based");
        }
    }

    public String location() {
        return line + ":" + column;
    }
}
