package org.learningfactory.mica;

import java.util.List;
import java.util.Objects;

public sealed interface Stmt permits Stmt.Expression, Stmt.Print, Stmt.Let, Stmt.Block,
        Stmt.If, Stmt.While {
    record Expression(Expr expression, Token terminator) implements Stmt {
        public Expression { Objects.requireNonNull(expression); Objects.requireNonNull(terminator); }
    }
    record Print(Token keyword, Expr expression) implements Stmt {
        public Print { Objects.requireNonNull(keyword); Objects.requireNonNull(expression); }
    }
    record Let(Token name, Expr initializer) implements Stmt {
        public Let { Objects.requireNonNull(name); Objects.requireNonNull(initializer); }
    }
    record Block(Token open, List<Stmt> statements) implements Stmt {
        public Block { Objects.requireNonNull(open); statements = List.copyOf(statements); }
    }
    record If(Token keyword, Expr condition, Stmt thenBranch, Stmt elseBranch) implements Stmt {
        public If { Objects.requireNonNull(keyword); Objects.requireNonNull(condition); Objects.requireNonNull(thenBranch); }
    }
    record While(Token keyword, Expr condition, Stmt body) implements Stmt {
        public While { Objects.requireNonNull(keyword); Objects.requireNonNull(condition); Objects.requireNonNull(body); }
    }
}
