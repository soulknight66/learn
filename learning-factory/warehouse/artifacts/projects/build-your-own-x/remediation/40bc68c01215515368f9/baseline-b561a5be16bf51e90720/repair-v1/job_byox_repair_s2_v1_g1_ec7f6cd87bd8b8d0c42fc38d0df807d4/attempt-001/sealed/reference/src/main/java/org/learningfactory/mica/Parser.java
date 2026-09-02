package org.learningfactory.mica;

import java.util.ArrayList;
import java.util.List;

public final class Parser {
    private final List<Token> tokens;
    private int current;
    private List<Stmt> parsed;

    public Parser(List<Token> tokens) {
        if (tokens == null || tokens.isEmpty()) {
            throw new MicaException(MicaException.Kind.PARSE, 1, 1, "token stream must contain EOF");
        }
        this.tokens = List.copyOf(tokens);
    }

    public List<Stmt> parse() {
        if (parsed != null) return parsed;
        List<Stmt> statements = new ArrayList<>();
        while (!isAtEnd()) statements.add(declaration());
        parsed = List.copyOf(statements);
        return parsed;
    }

    private Stmt declaration() {
        if (match(TokenType.LET)) return letDeclaration();
        return statement();
    }

    private Stmt letDeclaration() {
        Token name = consume(TokenType.IDENTIFIER, "expected variable name after 'let'");
        consume(TokenType.EQUAL, "expected '=' after variable name");
        Expr initializer = expression();
        consume(TokenType.SEMICOLON, "expected ';' after variable declaration");
        return new Stmt.Let(name, initializer);
    }

    private Stmt statement() {
        if (match(TokenType.PRINT)) return printStatement(previous());
        if (match(TokenType.IF)) return ifStatement(previous());
        if (match(TokenType.WHILE)) return whileStatement(previous());
        if (match(TokenType.LEFT_BRACE)) return new Stmt.Block(previous(), block());
        return expressionStatement();
    }

    private Stmt printStatement(Token keyword) {
        Expr value = expression();
        consume(TokenType.SEMICOLON, "expected ';' after value");
        return new Stmt.Print(keyword, value);
    }

    private Stmt ifStatement(Token keyword) {
        consume(TokenType.LEFT_PAREN, "expected '(' after 'if'");
        Expr condition = expression();
        consume(TokenType.RIGHT_PAREN, "expected ')' after condition");
        Stmt thenBranch = statement();
        Stmt elseBranch = null;
        if (match(TokenType.ELSE)) elseBranch = statement();
        return new Stmt.If(keyword, condition, thenBranch, elseBranch);
    }

    private Stmt whileStatement(Token keyword) {
        consume(TokenType.LEFT_PAREN, "expected '(' after 'while'");
        Expr condition = expression();
        consume(TokenType.RIGHT_PAREN, "expected ')' after condition");
        return new Stmt.While(keyword, condition, statement());
    }

    private List<Stmt> block() {
        List<Stmt> statements = new ArrayList<>();
        while (!check(TokenType.RIGHT_BRACE) && !isAtEnd()) statements.add(declaration());
        consume(TokenType.RIGHT_BRACE, "expected '}' after block");
        return statements;
    }

    private Stmt expressionStatement() {
        Expr value = expression();
        Token terminator = consume(TokenType.SEMICOLON, "expected ';' after expression");
        return new Stmt.Expression(value, terminator);
    }

    private Expr expression() {
        return assignment();
    }

    private Expr assignment() {
        Expr expression = or();
        if (match(TokenType.EQUAL)) {
            Token equals = previous();
            Expr value = assignment();
            if (expression instanceof Expr.Variable variable) return new Expr.Assign(variable.name(), value);
            throw error(equals, "invalid assignment target");
        }
        return expression;
    }

    private Expr or() {
        Expr expression = and();
        while (match(TokenType.OR)) expression = new Expr.Logical(expression, previous(), and());
        return expression;
    }

    private Expr and() {
        Expr expression = equality();
        while (match(TokenType.AND)) expression = new Expr.Logical(expression, previous(), equality());
        return expression;
    }

    private Expr equality() {
        Expr expression = comparison();
        while (match(TokenType.BANG_EQUAL, TokenType.EQUAL_EQUAL)) {
            expression = new Expr.Binary(expression, previous(), comparison());
        }
        return expression;
    }

    private Expr comparison() {
        Expr expression = term();
        while (match(TokenType.GREATER, TokenType.GREATER_EQUAL, TokenType.LESS, TokenType.LESS_EQUAL)) {
            expression = new Expr.Binary(expression, previous(), term());
        }
        return expression;
    }

    private Expr term() {
        Expr expression = factor();
        while (match(TokenType.MINUS, TokenType.PLUS)) {
            expression = new Expr.Binary(expression, previous(), factor());
        }
        return expression;
    }

    private Expr factor() {
        Expr expression = unary();
        while (match(TokenType.SLASH, TokenType.STAR)) {
            expression = new Expr.Binary(expression, previous(), unary());
        }
        return expression;
    }

    private Expr unary() {
        if (match(TokenType.BANG, TokenType.MINUS)) return new Expr.Unary(previous(), unary());
        return primary();
    }

    private Expr primary() {
        if (match(TokenType.FALSE)) return new Expr.Literal(previous(), false);
        if (match(TokenType.TRUE)) return new Expr.Literal(previous(), true);
        if (match(TokenType.NIL)) return new Expr.Literal(previous(), null);
        if (match(TokenType.NUMBER, TokenType.STRING)) return new Expr.Literal(previous(), previous().literal());
        if (match(TokenType.IDENTIFIER)) return new Expr.Variable(previous());
        if (match(TokenType.LEFT_PAREN)) {
            Token open = previous();
            Expr expression = expression();
            consume(TokenType.RIGHT_PAREN, "expected ')' after expression");
            return new Expr.Grouping(open, expression);
        }
        throw error(peek(), "expected expression");
    }

    private boolean match(TokenType... types) {
        for (TokenType type : types) {
            if (check(type)) {
                advance();
                return true;
            }
        }
        return false;
    }

    private Token consume(TokenType type, String message) {
        if (check(type)) return advance();
        throw error(peek(), message);
    }

    private boolean check(TokenType type) {
        if (current >= tokens.size()) return false;
        return peek().type() == type;
    }

    private Token advance() {
        if (current < tokens.size()) current++;
        return previous();
    }

    private boolean isAtEnd() {
        return check(TokenType.EOF);
    }

    private Token peek() {
        if (current < tokens.size()) return tokens.get(current);
        Token last = tokens.get(tokens.size() - 1);
        throw error(last, "token stream is missing EOF");
    }

    private Token previous() {
        return tokens.get(current - 1);
    }

    private static MicaException error(Token token, String message) {
        return new MicaException(MicaException.Kind.PARSE, token.line(), token.column(), message);
    }
}
