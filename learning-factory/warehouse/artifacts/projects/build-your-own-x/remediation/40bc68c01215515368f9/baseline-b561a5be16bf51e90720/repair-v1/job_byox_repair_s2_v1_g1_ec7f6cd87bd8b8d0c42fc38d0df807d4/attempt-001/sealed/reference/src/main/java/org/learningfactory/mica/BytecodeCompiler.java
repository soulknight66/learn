package org.learningfactory.mica;

import java.util.ArrayList;
import java.util.List;

public final class BytecodeCompiler {
    private final List<Instruction> code = new ArrayList<>();
    private final List<Object> constants = new ArrayList<>();

    public BytecodeProgram compile(List<Stmt> statements) {
        if (statements == null) {
            throw new MicaException(MicaException.Kind.RUNTIME, 1, 1, "statements must not be null");
        }
        code.clear();
        constants.clear();
        for (Stmt statement : statements) compile(statement);
        emit(OpCode.HALT, null, 1, 1);
        return new BytecodeProgram(code, constants);
    }

    private void compile(Stmt statement) {
        if (statement == null) throw runtime(1, 1, "null statement");
        Token statementToken = location(statement);
        emit(OpCode.TICK, null, statementToken);
        if (statement instanceof Stmt.Expression expression) {
            compile(expression.expression());
            emit(OpCode.POP, null, expression.terminator());
        } else if (statement instanceof Stmt.Print print) {
            compile(print.expression());
            emit(OpCode.PRINT, null, print.keyword());
        } else if (statement instanceof Stmt.Let let) {
            compile(let.initializer());
            emit(OpCode.DEFINE, let.name().lexeme(), let.name());
        } else if (statement instanceof Stmt.Block block) {
            emit(OpCode.ENTER_SCOPE, null, block.open());
            for (Stmt child : block.statements()) compile(child);
            emit(OpCode.EXIT_SCOPE, null, block.open());
        } else if (statement instanceof Stmt.If conditional) {
            compileIf(conditional);
        } else if (statement instanceof Stmt.While loop) {
            compileWhile(loop);
        } else {
            throw runtime(1, 1, "unknown statement node");
        }
    }

    private void compileIf(Stmt.If conditional) {
        compile(conditional.condition());
        int elseJump = emit(OpCode.JUMP_IF_FALSE, null, conditional.keyword());
        emit(OpCode.POP, null, conditional.keyword());
        compile(conditional.thenBranch());
        int endJump = emit(OpCode.JUMP, null, conditional.keyword());
        patch(elseJump, code.size());
        emit(OpCode.POP, null, conditional.keyword());
        if (conditional.elseBranch() != null) compile(conditional.elseBranch());
        patch(endJump, code.size());
    }

    private void compileWhile(Stmt.While loop) {
        int loopStart = code.size();
        compile(loop.condition());
        int exitJump = emit(OpCode.JUMP_IF_FALSE, null, loop.keyword());
        emit(OpCode.POP, null, loop.keyword());
        compile(loop.body());
        emit(OpCode.LOOP, loopStart, loop.keyword());
        patch(exitJump, code.size());
        emit(OpCode.POP, null, loop.keyword());
    }

    private void compile(Expr expression) {
        if (expression == null) throw runtime(1, 1, "null expression");
        if (expression instanceof Expr.Literal literal) {
            compileLiteral(literal);
        } else if (expression instanceof Expr.Grouping grouping) {
            compile(grouping.expression());
        } else if (expression instanceof Expr.Variable variable) {
            emit(OpCode.GET, variable.name().lexeme(), variable.name());
        } else if (expression instanceof Expr.Assign assign) {
            compile(assign.value());
            emit(OpCode.SET, assign.name().lexeme(), assign.name());
        } else if (expression instanceof Expr.Unary unary) {
            compile(unary.right());
            OpCode op = switch (unary.operator().type()) {
                case BANG -> OpCode.NOT;
                case MINUS -> OpCode.NEGATE;
                default -> throw Values.runtime(unary.operator(), "invalid unary operator");
            };
            emit(op, null, unary.operator());
        } else if (expression instanceof Expr.Binary binary) {
            compile(binary.left());
            compile(binary.right());
            emit(binaryOpcode(binary.operator()), null, binary.operator());
        } else if (expression instanceof Expr.Logical logical) {
            compileLogical(logical);
        } else {
            throw runtime(1, 1, "unknown expression node");
        }
    }

    private void compileLiteral(Expr.Literal literal) {
        if (literal.value() == null) {
            emit(OpCode.NIL, null, literal.token());
        } else if (literal.value().equals(true)) {
            emit(OpCode.TRUE, null, literal.token());
        } else if (literal.value().equals(false)) {
            emit(OpCode.FALSE, null, literal.token());
        } else {
            int index = constants.size();
            constants.add(literal.value());
            emit(OpCode.CONSTANT, index, literal.token());
        }
    }

    private void compileLogical(Expr.Logical logical) {
        compile(logical.left());
        if (logical.operator().type() == TokenType.AND) {
            int endJump = emit(OpCode.JUMP_IF_FALSE, null, logical.operator());
            emit(OpCode.POP, null, logical.operator());
            compile(logical.right());
            emit(OpCode.ASSERT_BOOL, null, logical.operator());
            patch(endJump, code.size());
        } else if (logical.operator().type() == TokenType.OR) {
            int rightJump = emit(OpCode.JUMP_IF_FALSE, null, logical.operator());
            int endJump = emit(OpCode.JUMP, null, logical.operator());
            patch(rightJump, code.size());
            emit(OpCode.POP, null, logical.operator());
            compile(logical.right());
            emit(OpCode.ASSERT_BOOL, null, logical.operator());
            patch(endJump, code.size());
        } else {
            throw Values.runtime(logical.operator(), "invalid logical operator");
        }
    }

    private static OpCode binaryOpcode(Token operator) {
        return switch (operator.type()) {
            case EQUAL_EQUAL -> OpCode.EQUAL;
            case BANG_EQUAL -> OpCode.NOT_EQUAL;
            case GREATER -> OpCode.GREATER;
            case GREATER_EQUAL -> OpCode.GREATER_EQUAL;
            case LESS -> OpCode.LESS;
            case LESS_EQUAL -> OpCode.LESS_EQUAL;
            case PLUS -> OpCode.ADD;
            case MINUS -> OpCode.SUBTRACT;
            case STAR -> OpCode.MULTIPLY;
            case SLASH -> OpCode.DIVIDE;
            default -> throw Values.runtime(operator, "invalid binary operator");
        };
    }

    private int emit(OpCode op, Object operand, Token token) {
        return emit(op, operand, token.line(), token.column());
    }

    private int emit(OpCode op, Object operand, int line, int column) {
        code.add(new Instruction(op, operand, line, column));
        return code.size() - 1;
    }

    private void patch(int index, int target) {
        Instruction original = code.get(index);
        code.set(index, new Instruction(original.op(), target, original.line(), original.column()));
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

    private static MicaException runtime(int line, int column, String detail) {
        return new MicaException(MicaException.Kind.RUNTIME, line, column, detail);
    }
}
