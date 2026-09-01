package dev.learningfactory.sprig;

import java.util.List;

/** Suggested precedence-based parsing stage. */
final class Parser {
    private final List<Token> tokens;

    Parser(List<Token> tokens) {
        this.tokens = List.copyOf(tokens);
    }

    Ast.Program parse() throws CompileFailure {
        throw CompileFailure.at("E_NOT_IMPLEMENTED", 1, 1,
                "implement parsing (token count " + tokens.size() + ")");
    }
}

