package dev.learningfactory.sprig;

import java.util.ArrayList;
import java.util.List;

final class Lexer {
    private static final int MAX_TOKENS = 100_000;

    private final String source;
    private final List<Token> tokens = new ArrayList<>();
    private int index;
    private int line = 1;
    private int column = 1;

    Lexer(String source) {
        this.source = source;
    }

    List<Token> scan() throws CompileFailure {
        while (!atEnd()) {
            skipTrivia();
            if (atEnd()) break;
            scanToken();
        }
        tokens.add(new Token(TokenType.EOF, "", line, column));
        return List.copyOf(tokens);
    }

    private void skipTrivia() {
        boolean again;
        do {
            again = false;
            while (!atEnd()) {
                char c = peek();
                if (c == ' ' || c == '\t' || c == '\n' || c == '\r') {
                    advance();
                } else {
                    break;
                }
            }
            if (!atEnd() && peek() == '/' && peekNext() == '/') {
                advance();
                advance();
                while (!atEnd() && peek() != '\n' && peek() != '\r') advance();
                again = true;
            }
        } while (again);
    }

    private void scanToken() throws CompileFailure {
        int start = index;
        int startLine = line;
        int startColumn = column;
        char c = advance();
        if (isIdentifierStart(c)) {
            while (isIdentifierPart(peek())) advance();
            String text = source.substring(start, index);
            add(keyword(text), text, startLine, startColumn);
            return;
        }
        if (isDigit(c)) {
            if (c == '0') {
                add(TokenType.INTEGER, "0", startLine, startColumn);
                return;
            }
            long value = c - '0';
            while (isDigit(peek())) {
                value = value * 10 + (advance() - '0');
                if (value > Integer.MAX_VALUE) {
                    while (isDigit(peek())) advance();
                    throw CompileFailure.at("E_INT_RANGE", startLine, startColumn,
                            "integer literal exceeds 2147483647");
                }
            }
            add(TokenType.INTEGER, source.substring(start, index), startLine, startColumn);
            return;
        }

        TokenType type = switch (c) {
            case '(' -> TokenType.LEFT_PAREN;
            case ')' -> TokenType.RIGHT_PAREN;
            case '{' -> TokenType.LEFT_BRACE;
            case '}' -> TokenType.RIGHT_BRACE;
            case ';' -> TokenType.SEMICOLON;
            case '+' -> TokenType.PLUS;
            case '*' -> TokenType.STAR;
            case '/' -> TokenType.SLASH;
            case '%' -> TokenType.PERCENT;
            case '-' -> match('>') ? TokenType.ARROW : TokenType.MINUS;
            case '=' -> match('=') ? TokenType.EQUAL_EQUAL : TokenType.ASSIGN;
            case '!' -> match('=') ? TokenType.BANG_EQUAL : TokenType.BANG;
            case '<' -> match('=') ? TokenType.LESS_EQUAL : TokenType.LESS;
            case '>' -> match('=') ? TokenType.GREATER_EQUAL : TokenType.GREATER;
            case '&' -> {
                if (!match('&')) {
                    throw CompileFailure.at("E_CHAR", startLine, startColumn,
                            "a lone '&' is not an operator");
                }
                yield TokenType.AND_AND;
            }
            case '|' -> {
                if (!match('|')) {
                    throw CompileFailure.at("E_CHAR", startLine, startColumn,
                            "a lone '|' is not an operator");
                }
                yield TokenType.OR_OR;
            }
            default -> throw CompileFailure.at("E_CHAR", startLine, startColumn,
                    "unexpected character U+" + String.format("%04X", (int) c));
        };
        add(type, source.substring(start, index), startLine, startColumn);
    }

    private void add(TokenType type, String text, int tokenLine, int tokenColumn)
            throws CompileFailure {
        if (tokens.size() >= MAX_TOKENS) {
            throw CompileFailure.at("E_LIMIT", tokenLine, tokenColumn,
                    "token limit of " + MAX_TOKENS + " exceeded");
        }
        tokens.add(new Token(type, text, tokenLine, tokenColumn));
    }

    private static TokenType keyword(String text) {
        return switch (text) {
            case "fn" -> TokenType.FN;
            case "main" -> TokenType.MAIN;
            case "Int" -> TokenType.INT;
            case "Bool" -> TokenType.BOOL;
            case "let" -> TokenType.LET;
            case "print" -> TokenType.PRINT;
            case "if" -> TokenType.IF;
            case "else" -> TokenType.ELSE;
            case "while" -> TokenType.WHILE;
            case "return" -> TokenType.RETURN;
            case "true" -> TokenType.TRUE;
            case "false" -> TokenType.FALSE;
            default -> TokenType.IDENTIFIER;
        };
    }

    private boolean match(char expected) {
        if (atEnd() || peek() != expected) return false;
        advance();
        return true;
    }

    private char advance() {
        char c = source.charAt(index++);
        if (c == '\r') {
            if (!atEnd() && source.charAt(index) == '\n') index++;
            line++;
            column = 1;
        } else if (c == '\n') {
            line++;
            column = 1;
        } else {
            column++;
        }
        return c;
    }

    private char peek() {
        return atEnd() ? '\0' : source.charAt(index);
    }

    private char peekNext() {
        return index + 1 >= source.length() ? '\0' : source.charAt(index + 1);
    }

    private boolean atEnd() {
        return index >= source.length();
    }

    private static boolean isIdentifierStart(char c) {
        return c == '_' || c >= 'A' && c <= 'Z' || c >= 'a' && c <= 'z';
    }

    private static boolean isIdentifierPart(char c) {
        return isIdentifierStart(c) || isDigit(c);
    }

    private static boolean isDigit(char c) {
        return c >= '0' && c <= '9';
    }
}
