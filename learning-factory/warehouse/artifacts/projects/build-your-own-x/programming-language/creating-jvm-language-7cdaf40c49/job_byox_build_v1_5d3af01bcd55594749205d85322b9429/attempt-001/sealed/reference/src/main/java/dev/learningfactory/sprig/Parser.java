package dev.learningfactory.sprig;

import java.util.ArrayList;
import java.util.List;

final class Parser {
    private final List<Token> tokens;
    private int current;
    private int statementNesting;
    private int recursiveExpressionNesting;

    Parser(List<Token> tokens) {
        this.tokens = List.copyOf(tokens);
    }

    Ast.Program parse() throws CompileFailure {
        Token start = consume(TokenType.FN, "expected 'fn'");
        consume(TokenType.MAIN, "expected 'main'");
        consume(TokenType.LEFT_PAREN, "expected '('");
        consume(TokenType.RIGHT_PAREN, "expected ')'");
        consume(TokenType.ARROW, "expected '->'");
        consume(TokenType.INT, "expected return type 'Int'");
        List<Ast.Stmt> body = block();
        consume(TokenType.EOF, "unexpected trailing input");
        return new Ast.Program(body, start.pos());
    }

    private List<Ast.Stmt> block() throws CompileFailure {
        Token open = consume(TokenType.LEFT_BRACE, "expected '{'");
        statementNesting++;
        if (statementNesting > Ast.MAX_NESTING) {
            throw CompileFailure.at("E_LIMIT", open.line(), open.column(),
                    "statement nesting exceeds " + Ast.MAX_NESTING);
        }
        List<Ast.Stmt> statements = new ArrayList<>();
        while (!check(TokenType.RIGHT_BRACE) && !check(TokenType.EOF)) {
            statements.add(statement());
        }
        consume(TokenType.RIGHT_BRACE, "expected '}'");
        statementNesting--;
        return List.copyOf(statements);
    }

    private Ast.Stmt statement() throws CompileFailure {
        if (match(TokenType.LET)) {
            Token keyword = previous();
            Token name = consume(TokenType.IDENTIFIER, "expected variable name");
            consume(TokenType.ASSIGN, "expected '=' after variable name");
            Ast.Expr initializer = expression();
            consume(TokenType.SEMICOLON, "expected ';' after declaration");
            return new Ast.Let(name.text(), initializer, keyword.pos());
        }
        if (match(TokenType.PRINT)) {
            Token keyword = previous();
            Ast.Expr value = expression();
            consume(TokenType.SEMICOLON, "expected ';' after print value");
            return new Ast.Print(value, keyword.pos());
        }
        if (match(TokenType.IF)) {
            Token keyword = previous();
            consume(TokenType.LEFT_PAREN, "expected '(' after 'if'");
            Ast.Expr condition = expression();
            consume(TokenType.RIGHT_PAREN, "expected ')' after condition");
            List<Ast.Stmt> thenBranch = block();
            consume(TokenType.ELSE, "expected 'else'");
            List<Ast.Stmt> elseBranch = block();
            return new Ast.If(condition, thenBranch, elseBranch, keyword.pos());
        }
        if (match(TokenType.WHILE)) {
            Token keyword = previous();
            consume(TokenType.LEFT_PAREN, "expected '(' after 'while'");
            Ast.Expr condition = expression();
            consume(TokenType.RIGHT_PAREN, "expected ')' after condition");
            return new Ast.While(condition, block(), keyword.pos());
        }
        if (match(TokenType.RETURN)) {
            Token keyword = previous();
            Ast.Expr value = expression();
            consume(TokenType.SEMICOLON, "expected ';' after return value");
            return new Ast.Return(value, keyword.pos());
        }
        if (check(TokenType.IDENTIFIER)) {
            Token name = advance();
            consume(TokenType.ASSIGN, "expected '=' after variable name");
            Ast.Expr value = expression();
            consume(TokenType.SEMICOLON, "expected ';' after assignment");
            return new Ast.Assign(name.text(), value, name.pos());
        }
        throw syntax(peek(), "expected a statement");
    }

    private Ast.Expr expression() throws CompileFailure {
        return or();
    }

    private Ast.Expr or() throws CompileFailure {
        return leftAssociative(this::and, TokenType.OR_OR);
    }

    private Ast.Expr and() throws CompileFailure {
        return leftAssociative(this::equality, TokenType.AND_AND);
    }

    private Ast.Expr equality() throws CompileFailure {
        return leftAssociative(this::relation, TokenType.EQUAL_EQUAL,
                TokenType.BANG_EQUAL);
    }

    private Ast.Expr relation() throws CompileFailure {
        return leftAssociative(this::term, TokenType.LESS, TokenType.LESS_EQUAL,
                TokenType.GREATER, TokenType.GREATER_EQUAL);
    }

    private Ast.Expr term() throws CompileFailure {
        return leftAssociative(this::factor, TokenType.PLUS, TokenType.MINUS);
    }

    private Ast.Expr factor() throws CompileFailure {
        return leftAssociative(this::unary, TokenType.STAR, TokenType.SLASH,
                TokenType.PERCENT);
    }

    private Ast.Expr leftAssociative(ExpressionParser operand, TokenType... operators)
            throws CompileFailure {
        Ast.Expr expression = operand.parse();
        while (match(operators)) {
            Token operator = previous();
            Ast.Expr right = operand.parse();
            int depth = 1 + Math.max(expression.depth(), right.depth());
            if (depth > Ast.MAX_NESTING) {
                throw CompileFailure.at("E_LIMIT", operator.line(), operator.column(),
                        "expression nesting exceeds " + Ast.MAX_NESTING);
            }
            expression = new Ast.Binary(operator.type(), expression, right,
                    operator.pos(), depth);
        }
        return expression;
    }

    private Ast.Expr unary() throws CompileFailure {
        if (match(TokenType.BANG, TokenType.MINUS)) {
            Token operator = previous();
            enterExpression(operator);
            Ast.Expr operand;
            try {
                operand = unary();
            } finally {
                recursiveExpressionNesting--;
            }
            int depth = operand.depth() + 1;
            if (depth > Ast.MAX_NESTING) {
                throw CompileFailure.at("E_LIMIT", operator.line(), operator.column(),
                        "expression nesting exceeds " + Ast.MAX_NESTING);
            }
            return new Ast.Unary(operator.type(), operand, operator.pos(), depth);
        }
        return primary();
    }

    private Ast.Expr primary() throws CompileFailure {
        if (match(TokenType.INTEGER)) {
            Token token = previous();
            return new Ast.Literal(Integer.parseInt(token.text()), Ast.Type.INT, token.pos());
        }
        if (match(TokenType.TRUE)) {
            Token token = previous();
            return new Ast.Literal(1, Ast.Type.BOOL, token.pos());
        }
        if (match(TokenType.FALSE)) {
            Token token = previous();
            return new Ast.Literal(0, Ast.Type.BOOL, token.pos());
        }
        if (match(TokenType.IDENTIFIER)) {
            Token token = previous();
            return new Ast.Variable(token.text(), token.pos());
        }
        if (match(TokenType.LEFT_PAREN)) {
            Token open = previous();
            enterExpression(open);
            Ast.Expr nested;
            try {
                nested = expression();
                consume(TokenType.RIGHT_PAREN, "expected ')' after expression");
            } finally {
                recursiveExpressionNesting--;
            }
            return nested;
        }
        throw syntax(peek(), "expected an expression");
    }

    private void enterExpression(Token token) throws CompileFailure {
        recursiveExpressionNesting++;
        if (recursiveExpressionNesting > Ast.MAX_NESTING) {
            throw CompileFailure.at("E_LIMIT", token.line(), token.column(),
                    "expression nesting exceeds " + Ast.MAX_NESTING);
        }
    }

    private Token consume(TokenType type, String message) throws CompileFailure {
        if (check(type)) return advance();
        throw syntax(peek(), message);
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

    private boolean check(TokenType type) {
        return peek().type() == type;
    }

    private Token advance() {
        if (!check(TokenType.EOF)) current++;
        return previous();
    }

    private Token peek() {
        return tokens.get(current);
    }

    private Token previous() {
        return tokens.get(current - 1);
    }

    private static CompileFailure syntax(Token token, String message) {
        return CompileFailure.at("E_SYNTAX", token.line(), token.column(), message);
    }

    @FunctionalInterface
    private interface ExpressionParser {
        Ast.Expr parse() throws CompileFailure;
    }
}

