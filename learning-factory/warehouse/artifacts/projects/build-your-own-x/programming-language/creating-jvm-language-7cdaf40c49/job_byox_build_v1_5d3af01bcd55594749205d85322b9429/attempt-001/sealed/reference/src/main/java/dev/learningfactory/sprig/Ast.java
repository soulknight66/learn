package dev.learningfactory.sprig;

import java.util.List;

final class Ast {
    private Ast() { }

    static final int MAX_NESTING = 256;

    record Pos(int line, int column) { }

    enum Type { INT, BOOL }

    record Program(List<Stmt> statements, Pos pos) {
        Program {
            statements = List.copyOf(statements);
        }
    }

    sealed interface Stmt permits Let, Assign, Print, If, While, Return {
        Pos pos();
    }

    record Let(String name, Expr initializer, Pos pos) implements Stmt { }
    record Assign(String name, Expr value, Pos pos) implements Stmt { }
    record Print(Expr value, Pos pos) implements Stmt { }
    record If(Expr condition, List<Stmt> thenBranch, List<Stmt> elseBranch, Pos pos)
            implements Stmt {
        If {
            thenBranch = List.copyOf(thenBranch);
            elseBranch = List.copyOf(elseBranch);
        }
    }
    record While(Expr condition, List<Stmt> body, Pos pos) implements Stmt {
        While {
            body = List.copyOf(body);
        }
    }
    record Return(Expr value, Pos pos) implements Stmt { }

    sealed interface Expr permits Literal, Variable, Unary, Binary {
        Pos pos();
        int depth();
    }

    record Literal(int value, Type type, Pos pos) implements Expr {
        @Override public int depth() { return 1; }
    }
    record Variable(String name, Pos pos) implements Expr {
        @Override public int depth() { return 1; }
    }
    record Unary(TokenType operator, Expr operand, Pos pos, int depth) implements Expr { }
    record Binary(TokenType operator, Expr left, Expr right, Pos pos, int depth)
            implements Expr { }
}

