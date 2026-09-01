package dev.learningfactory.sprig;

record Token(TokenType type, String text, int line, int column) {
    Ast.Pos pos() {
        return new Ast.Pos(line, column);
    }
}

