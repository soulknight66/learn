package dev.learningfactory.sprig;

import java.util.List;

/** Suggested lexical stage. Replace the placeholder with a bounded scanner. */
final class Lexer {
    private final String source;

    Lexer(String source) {
        this.source = source;
    }

    List<Token> scan() throws CompileFailure {
        throw CompileFailure.at("E_NOT_IMPLEMENTED", 1, 1,
                "implement tokenization (input length " + source.length() + ")");
    }
}

