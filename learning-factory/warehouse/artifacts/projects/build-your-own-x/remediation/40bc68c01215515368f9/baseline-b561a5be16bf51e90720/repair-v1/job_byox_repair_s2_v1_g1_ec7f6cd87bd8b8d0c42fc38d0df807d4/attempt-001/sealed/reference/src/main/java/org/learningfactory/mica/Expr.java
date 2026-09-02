package org.learningfactory.mica;

import java.util.Objects;

public sealed interface Expr permits Expr.Literal, Expr.Grouping, Expr.Unary, Expr.Binary,
        Expr.Logical, Expr.Variable, Expr.Assign {

    record Literal(Token token, Object value) implements Expr {
        public Literal { Objects.requireNonNull(token, "token"); }
    }

    record Grouping(Token open, Expr expression) implements Expr {
        public Grouping {
            Objects.requireNonNull(open, "open");
            Objects.requireNonNull(expression, "expression");
        }
    }

    record Unary(Token operator, Expr right) implements Expr {
        public Unary {
            Objects.requireNonNull(operator, "operator");
            Objects.requireNonNull(right, "right");
        }
    }

    record Binary(Expr left, Token operator, Expr right) implements Expr {
        public Binary {
            Objects.requireNonNull(left, "left");
            Objects.requireNonNull(operator, "operator");
            Objects.requireNonNull(right, "right");
        }
    }

    record Logical(Expr left, Token operator, Expr right) implements Expr {
        public Logical {
            Objects.requireNonNull(left, "left");
            Objects.requireNonNull(operator, "operator");
            Objects.requireNonNull(right, "right");
        }
    }

    record Variable(Token name) implements Expr {
        public Variable { Objects.requireNonNull(name, "name"); }
    }

    record Assign(Token name, Expr value) implements Expr {
        public Assign {
            Objects.requireNonNull(name, "name");
            Objects.requireNonNull(value, "value");
        }
    }
}
