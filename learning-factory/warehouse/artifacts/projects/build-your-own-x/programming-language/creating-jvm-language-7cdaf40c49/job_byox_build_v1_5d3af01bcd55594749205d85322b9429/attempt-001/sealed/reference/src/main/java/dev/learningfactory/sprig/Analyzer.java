package dev.learningfactory.sprig;

import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

final class Analyzer {
    private static final int MAX_LOCALS = 255;

    record Symbol(Ast.Type type, int slot) { }
    record Analysis(Map<String, Symbol> symbols) {
        Analysis {
            symbols = Map.copyOf(symbols);
        }
    }
    private record Flow(boolean terminates, LinkedHashSet<String> visible) { }

    private final LinkedHashMap<String, Symbol> symbols = new LinkedHashMap<>();

    Analysis analyze(Ast.Program program) throws CompileFailure {
        Flow flow = analyzeBlock(program.statements(), new LinkedHashSet<>());
        if (!flow.terminates()) {
            throw CompileFailure.at("E_MISSING_RETURN", program.pos(),
                    "not every reachable path returns an Int");
        }
        return new Analysis(symbols);
    }

    private Flow analyzeBlock(List<Ast.Stmt> statements, Set<String> incoming)
            throws CompileFailure {
        LinkedHashSet<String> visible = new LinkedHashSet<>(incoming);
        boolean terminated = false;
        for (Ast.Stmt statement : statements) {
            if (terminated) {
                throw CompileFailure.at("E_UNREACHABLE", statement.pos(),
                        "statement follows an unconditional return");
            }
            Flow flow = analyzeStatement(statement, visible);
            visible = flow.visible();
            terminated = flow.terminates();
        }
        return new Flow(terminated, visible);
    }

    private Flow analyzeStatement(Ast.Stmt statement, LinkedHashSet<String> visible)
            throws CompileFailure {
        if (statement instanceof Ast.Let let) {
            if (symbols.containsKey(let.name())) {
                throw CompileFailure.at("E_DUPLICATE", let.pos(),
                        "variable '" + let.name() + "' is already declared");
            }
            Ast.Type type = expressionType(let.initializer(), visible);
            if (symbols.size() >= MAX_LOCALS) {
                throw CompileFailure.at("E_LIMIT", let.pos(),
                        "local variable limit of " + MAX_LOCALS + " exceeded");
            }
            symbols.put(let.name(), new Symbol(type, symbols.size()));
            LinkedHashSet<String> outgoing = copy(visible);
            outgoing.add(let.name());
            return new Flow(false, outgoing);
        }
        if (statement instanceof Ast.Assign assign) {
            Symbol target = requireVisible(assign.name(), assign.pos(), visible);
            Ast.Type value = expressionType(assign.value(), visible);
            requireType(target.type(), value, assign.value().pos(),
                    "assignment to '" + assign.name() + "'");
            return new Flow(false, copy(visible));
        }
        if (statement instanceof Ast.Print print) {
            requireType(Ast.Type.INT, expressionType(print.value(), visible),
                    print.value().pos(), "print operand");
            return new Flow(false, copy(visible));
        }
        if (statement instanceof Ast.Return returnStatement) {
            requireType(Ast.Type.INT, expressionType(returnStatement.value(), visible),
                    returnStatement.value().pos(), "return value");
            return new Flow(true, copy(visible));
        }
        if (statement instanceof Ast.If conditional) {
            requireType(Ast.Type.BOOL, expressionType(conditional.condition(), visible),
                    conditional.condition().pos(), "if condition");
            Flow thenFlow = analyzeBlock(conditional.thenBranch(), visible);
            Flow elseFlow = analyzeBlock(conditional.elseBranch(), visible);
            LinkedHashSet<String> outgoing;
            if (thenFlow.terminates() && !elseFlow.terminates()) {
                outgoing = copy(elseFlow.visible());
            } else if (!thenFlow.terminates() && elseFlow.terminates()) {
                outgoing = copy(thenFlow.visible());
            } else {
                outgoing = copy(thenFlow.visible());
                outgoing.retainAll(elseFlow.visible());
            }
            return new Flow(thenFlow.terminates() && elseFlow.terminates(), outgoing);
        }
        if (statement instanceof Ast.While loop) {
            requireType(Ast.Type.BOOL, expressionType(loop.condition(), visible),
                    loop.condition().pos(), "while condition");
            analyzeBlock(loop.body(), visible);
            return new Flow(false, copy(visible));
        }
        throw new IllegalStateException("unknown statement: " + statement.getClass());
    }

    private Ast.Type expressionType(Ast.Expr expression, Set<String> visible)
            throws CompileFailure {
        if (expression instanceof Ast.Literal literal) return literal.type();
        if (expression instanceof Ast.Variable variable) {
            return requireVisible(variable.name(), variable.pos(), visible).type();
        }
        if (expression instanceof Ast.Unary unary) {
            Ast.Type operand = expressionType(unary.operand(), visible);
            Ast.Type required = unary.operator() == TokenType.BANG
                    ? Ast.Type.BOOL : Ast.Type.INT;
            requireType(required, operand, unary.operand().pos(), "unary operand");
            return required;
        }
        if (expression instanceof Ast.Binary binary) {
            Ast.Type left = expressionType(binary.left(), visible);
            Ast.Type right = expressionType(binary.right(), visible);
            return switch (binary.operator()) {
                case PLUS, MINUS, STAR, SLASH, PERCENT -> {
                    requireType(Ast.Type.INT, left, binary.left().pos(),
                            "arithmetic left operand");
                    requireType(Ast.Type.INT, right, binary.right().pos(),
                            "arithmetic right operand");
                    yield Ast.Type.INT;
                }
                case LESS, LESS_EQUAL, GREATER, GREATER_EQUAL -> {
                    requireType(Ast.Type.INT, left, binary.left().pos(),
                            "comparison left operand");
                    requireType(Ast.Type.INT, right, binary.right().pos(),
                            "comparison right operand");
                    yield Ast.Type.BOOL;
                }
                case AND_AND, OR_OR -> {
                    requireType(Ast.Type.BOOL, left, binary.left().pos(),
                            "logical left operand");
                    requireType(Ast.Type.BOOL, right, binary.right().pos(),
                            "logical right operand");
                    yield Ast.Type.BOOL;
                }
                case EQUAL_EQUAL, BANG_EQUAL -> {
                    if (left != right) {
                        throw CompileFailure.at("E_TYPE", binary.pos(),
                                "equality operands must have the same type");
                    }
                    yield Ast.Type.BOOL;
                }
                default -> throw new IllegalStateException(
                        "unexpected binary operator " + binary.operator());
            };
        }
        throw new IllegalStateException("unknown expression: " + expression.getClass());
    }

    private Symbol requireVisible(String name, Ast.Pos pos, Set<String> visible)
            throws CompileFailure {
        if (!visible.contains(name)) {
            throw CompileFailure.at("E_UNDECLARED", pos,
                    "variable '" + name + "' is not declared on this path");
        }
        return symbols.get(name);
    }

    private static void requireType(Ast.Type expected, Ast.Type actual, Ast.Pos pos,
            String context) throws CompileFailure {
        if (expected != actual) {
            throw CompileFailure.at("E_TYPE", pos,
                    context + " requires " + expected + " but found " + actual);
        }
    }

    private static LinkedHashSet<String> copy(Set<String> names) {
        return new LinkedHashSet<>(names);
    }
}

