package dev.learningfactory.sprig;

/** Token categories used by the suggested recursive-descent front end. */
enum TokenType {
    IDENTIFIER, INTEGER,
    FN, MAIN, INT, BOOL, LET, PRINT, IF, ELSE, WHILE, RETURN, TRUE, FALSE,
    LEFT_PAREN, RIGHT_PAREN, LEFT_BRACE, RIGHT_BRACE, SEMICOLON,
    ASSIGN, PLUS, MINUS, STAR, SLASH, PERCENT, BANG,
    EQUAL_EQUAL, BANG_EQUAL, LESS, LESS_EQUAL, GREATER, GREATER_EQUAL,
    AND_AND, OR_OR, ARROW, EOF
}

