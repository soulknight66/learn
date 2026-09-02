package org.learningfactory.mica;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public final class Lexer {
    private static final Map<String, TokenType> KEYWORDS = Map.ofEntries(
            Map.entry("and", TokenType.AND),
            Map.entry("else", TokenType.ELSE),
            Map.entry("false", TokenType.FALSE),
            Map.entry("if", TokenType.IF),
            Map.entry("let", TokenType.LET),
            Map.entry("nil", TokenType.NIL),
            Map.entry("or", TokenType.OR),
            Map.entry("print", TokenType.PRINT),
            Map.entry("true", TokenType.TRUE),
            Map.entry("while", TokenType.WHILE));

    private final String source;
    private final List<Token> tokens = new ArrayList<>();
    private int start;
    private int current;
    private int line = 1;
    private int column = 1;
    private int startLine;
    private int startColumn;
    private List<Token> scanned;

    public Lexer(String source) {
        if (source == null) {
            throw new MicaException(MicaException.Kind.LEX, 1, 1, "source must not be null");
        }
        this.source = source;
    }

    public List<Token> scanTokens() {
        if (scanned != null) return scanned;
        while (!isAtEnd()) {
            start = current;
            startLine = line;
            startColumn = column;
            scanToken();
        }
        tokens.add(new Token(TokenType.EOF, "", null, line, column));
        scanned = List.copyOf(tokens);
        return scanned;
    }

    private void scanToken() {
        char c = advance();
        switch (c) {
            case '(' -> add(TokenType.LEFT_PAREN);
            case ')' -> add(TokenType.RIGHT_PAREN);
            case '{' -> add(TokenType.LEFT_BRACE);
            case '}' -> add(TokenType.RIGHT_BRACE);
            case ',' -> add(TokenType.COMMA);
            case '-' -> add(TokenType.MINUS);
            case '+' -> add(TokenType.PLUS);
            case ';' -> add(TokenType.SEMICOLON);
            case '*' -> add(TokenType.STAR);
            case '!' -> add(match('=') ? TokenType.BANG_EQUAL : TokenType.BANG);
            case '=' -> add(match('=') ? TokenType.EQUAL_EQUAL : TokenType.EQUAL);
            case '<' -> add(match('=') ? TokenType.LESS_EQUAL : TokenType.LESS);
            case '>' -> add(match('=') ? TokenType.GREATER_EQUAL : TokenType.GREATER);
            case '/' -> {
                if (match('/')) {
                    while (peek() != '\n' && !isAtEnd()) advance();
                } else {
                    add(TokenType.SLASH);
                }
            }
            case ' ', '\r', '\t', '\n' -> { }
            case '"' -> string();
            default -> {
                if (isDigit(c)) number();
                else if (isIdentifierStart(c)) identifier();
                else throw lex(startLine, startColumn, "unexpected character '" + printable(c) + "'");
            }
        }
    }

    private void string() {
        StringBuilder value = new StringBuilder();
        while (!isAtEnd()) {
            char c = advance();
            if (c == '"') {
                add(TokenType.STRING, value.toString());
                return;
            }
            if (c != '\\') {
                value.append(c);
                continue;
            }

            int escapeLine = line;
            int escapeColumn = column - 1;
            if (isAtEnd()) {
                throw lex(startLine, startColumn, "unterminated string");
            }
            char escaped = advance();
            switch (escaped) {
                case 'n' -> value.append('\n');
                case 't' -> value.append('\t');
                case '"' -> value.append('"');
                case '\\' -> value.append('\\');
                default -> throw lex(escapeLine, escapeColumn,
                        "invalid escape '\\" + printable(escaped) + "'");
            }
        }
        throw lex(startLine, startColumn, "unterminated string");
    }

    private void number() {
        while (isDigit(peek())) advance();
        if (peek() == '.' && isDigit(peekNext())) {
            advance();
            while (isDigit(peek())) advance();
        }

        String text = source.substring(start, current);
        try {
            double value = Double.parseDouble(text);
            if (!Double.isFinite(value)) {
                throw lex(startLine, startColumn, "number literal is not finite");
            }
            add(TokenType.NUMBER, value);
        } catch (NumberFormatException exception) {
            throw lex(startLine, startColumn, "invalid number literal");
        }
    }

    private void identifier() {
        while (isIdentifierPart(peek())) advance();
        String text = source.substring(start, current);
        add(KEYWORDS.getOrDefault(text, TokenType.IDENTIFIER));
    }

    private boolean match(char expected) {
        if (isAtEnd() || source.charAt(current) != expected) return false;
        advance();
        return true;
    }

    private char peek() {
        return isAtEnd() ? '\0' : source.charAt(current);
    }

    private char peekNext() {
        return current + 1 >= source.length() ? '\0' : source.charAt(current + 1);
    }

    private char advance() {
        char c = source.charAt(current++);
        if (c == '\n') {
            line++;
            column = 1;
        } else {
            column++;
        }
        return c;
    }

    private boolean isAtEnd() {
        return current >= source.length();
    }

    private void add(TokenType type) {
        add(type, null);
    }

    private void add(TokenType type, Object literal) {
        tokens.add(new Token(type, source.substring(start, current), literal, startLine, startColumn));
    }

    private static boolean isDigit(char c) {
        return c >= '0' && c <= '9';
    }

    private static boolean isIdentifierStart(char c) {
        return c == '_' || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
    }

    private static boolean isIdentifierPart(char c) {
        return isIdentifierStart(c) || isDigit(c);
    }

    private static String printable(char c) {
        return switch (c) {
            case '\n' -> "\\n";
            case '\r' -> "\\r";
            case '\t' -> "\\t";
            default -> Character.toString(c);
        };
    }

    private static MicaException lex(int line, int column, String detail) {
        return new MicaException(MicaException.Kind.LEX, line, column, detail);
    }
}
