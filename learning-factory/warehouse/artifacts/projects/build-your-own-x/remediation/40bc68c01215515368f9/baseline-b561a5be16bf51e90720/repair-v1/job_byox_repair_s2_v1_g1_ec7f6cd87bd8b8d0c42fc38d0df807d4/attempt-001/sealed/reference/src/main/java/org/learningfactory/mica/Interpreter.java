package org.learningfactory.mica;

import java.util.ArrayList;
import java.util.List;

public final class Interpreter {
    public static final int EXECUTION_LIMIT = 100_000;

    private final List<String> output = new ArrayList<>();
    private Environment environment;
    private int steps;

    public List<String> execute(List<Stmt> statements) {
        if (statements == null) {
            throw new MicaException(MicaException.Kind.RUNTIME, 1, 1, "statements must not be null");
        }
        output.clear();
        environment = new Environment(null);
        steps = 0;
        for (Stmt statement : statements) execute(statement);
        return List.copyOf(output);
    }

    private void execute(Stmt statement) {
        if (statement == null) throw runtime(1, 1, "null statement");
        Token location = location(statement);
        if (steps >= EXECUTION_LIMIT) {
            throw new MicaException(MicaException.Kind.LIMIT, location.line(), location.column(),
                    "execution limit of " + EXECUTION_LIMIT + " statements exceeded");
        }
        steps++;

        if (statement instanceof Stmt.Expression expression) {
            evaluate(expression.expression());
        } else if (statement instanceof Stmt.Print print) {
            output.add(Values.render(evaluate(print.expression())));
        } else if (statement instanceof Stmt.Let let) {
            Object value = evaluate(let.initializer());
            environment.define(let.name(), value);
        } else if (statement instanceof Stmt.Block block) {
            executeBlock(block.statements(), new Environment(environment));
        } else if (statement instanceof Stmt.If conditional) {
            boolean condition = Values.bool(evaluate(conditional.condition()), conditional.keyword(), "if condition");
            if (condition) execute(conditional.thenBranch());
            else if (conditional.elseBranch() != null) execute(conditional.elseBranch());
        } else if (statement instanceof Stmt.While loop) {
            while (Values.bool(evaluate(loop.condition()), loop.keyword(), "while condition")) {
                execute(loop.body());
            }
        } else {
            throw runtime(location.line(), location.column(), "unknown statement node");
        }
    }

    private void executeBlock(List<Stmt> statements, Environment blockEnvironment) {
        Environment previous = environment;
        try {
            environment = blockEnvironment;
            for (Stmt statement : statements) execute(statement);
        } finally {
            environment = previous;
        }
    }

    private Object evaluate(Expr expression) {
        if (expression == null) throw runtime(1, 1, "null expression");
        if (expression instanceof Expr.Literal literal) return literal.value();
        if (expression instanceof Expr.Grouping grouping) return evaluate(grouping.expression());
        if (expression instanceof Expr.Variable variable) return environment.get(variable.name());
        if (expression instanceof Expr.Assign assign) {
            Object value = evaluate(assign.value());
            environment.assign(assign.name(), value);
            return value;
        }
        if (expression instanceof Expr.Unary unary) return evaluateUnary(unary);
        if (expression instanceof Expr.Binary binary) return evaluateBinary(binary);
        if (expression instanceof Expr.Logical logical) return evaluateLogical(logical);
        Token token = expressionLocation(expression);
        throw runtime(token.line(), token.column(), "unknown expression node");
    }

    private Object evaluateUnary(Expr.Unary unary) {
        Object right = evaluate(unary.right());
        return switch (unary.operator().type()) {
            case BANG -> !Values.bool(right, unary.operator(), "'!'");
            case MINUS -> -Values.number(right, unary.operator(), "unary '-'");
            default -> throw Values.runtime(unary.operator(), "invalid unary operator");
        };
    }

    private Object evaluateBinary(Expr.Binary binary) {
        Object left = evaluate(binary.left());
        Object right = evaluate(binary.right());
        Token operator = binary.operator();
        return switch (operator.type()) {
            case EQUAL_EQUAL -> Values.equal(left, right);
            case BANG_EQUAL -> !Values.equal(left, right);
            case GREATER -> numbers(left, right, operator, (a, b) -> a > b);
            case GREATER_EQUAL -> numbers(left, right, operator, (a, b) -> a >= b);
            case LESS -> numbers(left, right, operator, (a, b) -> a < b);
            case LESS_EQUAL -> numbers(left, right, operator, (a, b) -> a <= b);
            case MINUS -> Values.number(left, operator, "'-'") - Values.number(right, operator, "'-'");
            case STAR -> Values.number(left, operator, "'*'") * Values.number(right, operator, "'*'");
            case SLASH -> divide(left, right, operator);
            case PLUS -> plus(left, right, operator);
            default -> throw Values.runtime(operator, "invalid binary operator");
        };
    }

    private Object evaluateLogical(Expr.Logical logical) {
        boolean left = Values.bool(evaluate(logical.left()), logical.operator(),
                "'" + logical.operator().lexeme() + "'");
        if (logical.operator().type() == TokenType.OR) {
            if (left) return true;
        } else if (!left) {
            return false;
        }
        return Values.bool(evaluate(logical.right()), logical.operator(),
                "'" + logical.operator().lexeme() + "'");
    }

    private static Object plus(Object left, Object right, Token operator) {
        if (left instanceof Double a && right instanceof Double b) return a + b;
        if (left instanceof String a && right instanceof String b) return a + b;
        throw Values.runtime(operator, "'+' requires two numbers or two strings, got "
                + Values.typeName(left) + " and " + Values.typeName(right));
    }

    private static Object divide(Object left, Object right, Token operator) {
        double numerator = Values.number(left, operator, "'/'");
        double denominator = Values.number(right, operator, "'/'");
        if (denominator == 0.0) throw Values.runtime(operator, "division by zero");
        return numerator / denominator;
    }

    private static boolean numbers(Object left, Object right, Token operator, NumberPredicate predicate) {
        return predicate.test(Values.number(left, operator, "comparison"),
                Values.number(right, operator, "comparison"));
    }

    private static Token location(Stmt statement) {
        if (statement instanceof Stmt.Expression expression) return expression.terminator();
        if (statement instanceof Stmt.Print print) return print.keyword();
        if (statement instanceof Stmt.Let let) return let.name();
        if (statement instanceof Stmt.Block block) return block.open();
        if (statement instanceof Stmt.If conditional) return conditional.keyword();
        if (statement instanceof Stmt.While loop) return loop.keyword();
        throw runtime(1, 1, "unknown statement node");
    }

    private static Token expressionLocation(Expr expression) {
        if (expression instanceof Expr.Literal literal) return literal.token();
        if (expression instanceof Expr.Grouping grouping) return grouping.open();
        if (expression instanceof Expr.Unary unary) return unary.operator();
        if (expression instanceof Expr.Binary binary) return binary.operator();
        if (expression instanceof Expr.Logical logical) return logical.operator();
        if (expression instanceof Expr.Variable variable) return variable.name();
        if (expression instanceof Expr.Assign assign) return assign.name();
        throw runtime(1, 1, "unknown expression node");
    }

    private static MicaException runtime(int line, int column, String detail) {
        return new MicaException(MicaException.Kind.RUNTIME, line, column, detail);
    }

    @FunctionalInterface
    private interface NumberPredicate {
        boolean test(double left, double right);
    }
}
