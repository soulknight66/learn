package org.learningfactory.mica;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class VirtualMachine {
    public static final int EXECUTION_LIMIT = 100_000;
    public static final int RAW_INSTRUCTION_LIMIT = 1_000_000;

    private final List<Object> stack = new ArrayList<>();
    private final List<Map<String, Object>> scopes = new ArrayList<>();
    private final List<String> output = new ArrayList<>();
    private List<Instruction> code;
    private List<Object> constants;
    private int ip;
    private int steps;
    private int rawSteps;

    public List<String> execute(BytecodeProgram program) {
        reset(program);
        while (true) {
            if (ip < 0 || ip >= code.size()) throw runtime(1, 1, "instruction pointer left bytecode");
            Instruction instruction = code.get(ip);
            if (instruction == null) throw runtime(1, 1, "null instruction at index " + ip);
            if (instruction.line() < 1 || instruction.column() < 1) {
                throw runtime(1, 1, "instruction has invalid source location at index " + ip);
            }
            if (instruction.op() == null) throw runtime(instruction, "instruction has null opcode");
            if (rawSteps >= RAW_INSTRUCTION_LIMIT) {
                throw new MicaException(MicaException.Kind.LIMIT, instruction.line(), instruction.column(),
                        "raw instruction limit of " + RAW_INSTRUCTION_LIMIT + " exceeded");
            }
            rawSteps++;
            ip++;

            switch (instruction.op()) {
                case TICK -> tick(instruction);
                case CONSTANT -> push(constant(instruction), instruction);
                case NIL -> { noOperand(instruction); push(null, instruction); }
                case TRUE -> { noOperand(instruction); push(true, instruction); }
                case FALSE -> { noOperand(instruction); push(false, instruction); }
                case POP -> { noOperand(instruction); pop(instruction); }
                case GET -> get(instruction);
                case DEFINE -> define(instruction);
                case SET -> set(instruction);
                case EQUAL -> binary(instruction, (left, right, ignored) -> Values.equal(left, right));
                case NOT_EQUAL -> binary(instruction, (left, right, ignored) -> !Values.equal(left, right));
                case GREATER -> compare(instruction, Comparison.GREATER);
                case GREATER_EQUAL -> compare(instruction, Comparison.GREATER_EQUAL);
                case LESS -> compare(instruction, Comparison.LESS);
                case LESS_EQUAL -> compare(instruction, Comparison.LESS_EQUAL);
                case ADD -> binary(instruction, VirtualMachine::add);
                case SUBTRACT -> numeric(instruction, (left, right) -> left - right);
                case MULTIPLY -> numeric(instruction, (left, right) -> left * right);
                case DIVIDE -> divide(instruction);
                case NOT -> replaceTop(instruction,
                        value -> !Values.bool(value, token(instruction), "'!'"));
                case NEGATE -> replaceTop(instruction,
                        value -> -Values.number(value, token(instruction), "unary '-'"));
                case ASSERT_BOOL -> replaceTop(instruction,
                        value -> Values.bool(value, token(instruction), "logical operator"));
                case PRINT -> { noOperand(instruction); output.add(Values.render(pop(instruction))); }
                case JUMP -> jump(instruction);
                case JUMP_IF_FALSE -> jumpIfFalse(instruction);
                case LOOP -> jump(instruction);
                case ENTER_SCOPE -> { noOperand(instruction); scopes.add(new LinkedHashMap<>()); }
                case EXIT_SCOPE -> exitScope(instruction);
                case HALT -> {
                    noOperand(instruction);
                    if (!stack.isEmpty()) throw runtime(instruction, "operand stack is not empty at HALT");
                    if (scopes.size() != 1) throw runtime(instruction, "scope stack is unbalanced at HALT");
                    return List.copyOf(output);
                }
            }
        }
    }

    private void reset(BytecodeProgram program) {
        if (program == null) throw runtime(1, 1, "program must not be null");
        if (program.code() == null || program.constants() == null) {
            throw runtime(1, 1, "program code and constants must not be null");
        }
        code = program.code();
        constants = program.constants();
        stack.clear();
        scopes.clear();
        scopes.add(new LinkedHashMap<>());
        output.clear();
        ip = 0;
        steps = 0;
        rawSteps = 0;
    }

    private void tick(Instruction instruction) {
        noOperand(instruction);
        if (steps >= EXECUTION_LIMIT) {
            throw new MicaException(MicaException.Kind.LIMIT, instruction.line(), instruction.column(),
                    "execution limit of " + EXECUTION_LIMIT + " statements exceeded");
        }
        steps++;
    }

    private Object constant(Instruction instruction) {
        int index = integerOperand(instruction, "constant index");
        if (index < 0 || index >= constants.size()) throw runtime(instruction, "constant index out of range: " + index);
        Object value = constants.get(index);
        if (!(value instanceof Double || value instanceof String)) {
            throw runtime(instruction, "constant is not a number or string");
        }
        return value;
    }

    private void get(Instruction instruction) {
        String name = nameOperand(instruction);
        for (int i = scopes.size() - 1; i >= 0; i--) {
            if (scopes.get(i).containsKey(name)) {
                push(scopes.get(i).get(name), instruction);
                return;
            }
        }
        throw runtime(instruction, "undefined variable '" + name + "'");
    }

    private void define(Instruction instruction) {
        String name = nameOperand(instruction);
        Map<String, Object> current = scopes.get(scopes.size() - 1);
        if (current.containsKey(name)) {
            throw runtime(instruction, "variable '" + name + "' is already defined in this scope");
        }
        current.put(name, pop(instruction));
    }

    private void set(Instruction instruction) {
        String name = nameOperand(instruction);
        requireStack(1, instruction);
        for (int i = scopes.size() - 1; i >= 0; i--) {
            if (scopes.get(i).containsKey(name)) {
                scopes.get(i).put(name, peek());
                return;
            }
        }
        throw runtime(instruction, "undefined variable '" + name + "'");
    }

    private void compare(Instruction instruction, Comparison comparison) {
        binary(instruction, (left, right, token) -> {
            double a = Values.number(left, token, "comparison");
            double b = Values.number(right, token, "comparison");
            return switch (comparison) {
                case GREATER -> a > b;
                case GREATER_EQUAL -> a >= b;
                case LESS -> a < b;
                case LESS_EQUAL -> a <= b;
            };
        });
    }

    private void numeric(Instruction instruction, NumericOperation operation) {
        binary(instruction, (left, right, token) -> operation.apply(
                Values.number(left, token, "'" + symbol(instruction.op()) + "'"),
                Values.number(right, token, "'" + symbol(instruction.op()) + "'")));
    }

    private void divide(Instruction instruction) {
        binary(instruction, (left, right, token) -> {
            double numerator = Values.number(left, token, "'/'");
            double denominator = Values.number(right, token, "'/'");
            if (denominator == 0.0) throw Values.runtime(token, "division by zero");
            return numerator / denominator;
        });
    }

    private static Object add(Object left, Object right, Token token) {
        if (left instanceof Double a && right instanceof Double b) return a + b;
        if (left instanceof String a && right instanceof String b) return a + b;
        throw Values.runtime(token, "'+' requires two numbers or two strings, got "
                + Values.typeName(left) + " and " + Values.typeName(right));
    }

    private void binary(Instruction instruction, BinaryOperation operation) {
        noOperand(instruction);
        requireStack(2, instruction);
        Object right = pop(instruction);
        Object left = pop(instruction);
        push(operation.apply(left, right, token(instruction)), instruction);
    }

    private void replaceTop(Instruction instruction, UnaryOperation operation) {
        noOperand(instruction);
        requireStack(1, instruction);
        Object value = pop(instruction);
        push(operation.apply(value), instruction);
    }

    private void jump(Instruction instruction) {
        ip = jumpTarget(instruction);
    }

    private void jumpIfFalse(Instruction instruction) {
        int target = jumpTarget(instruction);
        requireStack(1, instruction);
        boolean condition = Values.bool(peek(), token(instruction), "condition");
        if (!condition) ip = target;
    }

    private void exitScope(Instruction instruction) {
        noOperand(instruction);
        if (scopes.size() <= 1) throw runtime(instruction, "cannot exit global scope");
        scopes.remove(scopes.size() - 1);
    }

    private int jumpTarget(Instruction instruction) {
        int target = integerOperand(instruction, "jump target");
        if (target < 0 || target >= code.size()) throw runtime(instruction, "jump target out of range: " + target);
        return target;
    }

    private int integerOperand(Instruction instruction, String description) {
        if (!(instruction.operand() instanceof Integer value)) {
            throw runtime(instruction, description + " must be an integer");
        }
        return value;
    }

    private String nameOperand(Instruction instruction) {
        if (!(instruction.operand() instanceof String name) || name.isEmpty()) {
            throw runtime(instruction, "variable operand must be a non-empty string");
        }
        return name;
    }

    private void noOperand(Instruction instruction) {
        if (instruction.operand() != null) throw runtime(instruction, instruction.op() + " takes no operand");
    }

    private void push(Object value, Instruction instruction) {
        stack.add(value);
    }

    private Object pop(Instruction instruction) {
        requireStack(1, instruction);
        return stack.remove(stack.size() - 1);
    }

    private Object peek() {
        return stack.get(stack.size() - 1);
    }

    private void requireStack(int count, Instruction instruction) {
        if (stack.size() < count) throw runtime(instruction, "operand stack underflow");
    }

    private static Token token(Instruction instruction) {
        return new Token(TokenType.EOF, "", null, instruction.line(), instruction.column());
    }

    private static String symbol(OpCode op) {
        return switch (op) {
            case SUBTRACT -> "-";
            case MULTIPLY -> "*";
            default -> op.name();
        };
    }

    private static MicaException runtime(Instruction instruction, String detail) {
        return runtime(instruction.line(), instruction.column(), detail);
    }

    private static MicaException runtime(int line, int column, String detail) {
        return new MicaException(MicaException.Kind.RUNTIME, line, column, detail);
    }

    private enum Comparison { GREATER, GREATER_EQUAL, LESS, LESS_EQUAL }

    @FunctionalInterface
    private interface BinaryOperation { Object apply(Object left, Object right, Token token); }

    @FunctionalInterface
    private interface UnaryOperation { Object apply(Object value); }

    @FunctionalInterface
    private interface NumericOperation { double apply(double left, double right); }
}
