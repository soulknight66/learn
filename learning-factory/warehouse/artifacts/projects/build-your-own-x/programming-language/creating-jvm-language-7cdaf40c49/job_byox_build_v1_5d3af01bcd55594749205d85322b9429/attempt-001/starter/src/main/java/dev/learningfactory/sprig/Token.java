package dev.learningfactory.sprig;

/** A token and the position of its first source character. */
record Token(TokenType type, String text, int line, int column) { }

