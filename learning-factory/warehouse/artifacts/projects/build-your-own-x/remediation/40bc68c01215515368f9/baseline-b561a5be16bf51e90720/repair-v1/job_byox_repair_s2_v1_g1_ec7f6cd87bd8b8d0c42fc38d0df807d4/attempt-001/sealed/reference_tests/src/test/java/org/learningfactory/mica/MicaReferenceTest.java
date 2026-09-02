package org.learningfactory.mica;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public final class MicaReferenceTest {
    private int passed;
    private int failed;

    public static void main(String[] args) {
        MicaReferenceTest suite = new MicaReferenceTest();
        suite.test("all punctuation and keyword tokens", suite::allTokens);
        suite.test("comments, newlines, and EOF location", suite::commentsAndEofLocation);
        suite.test("strings and lexical failures", suite::stringsAndLexicalFailures);
        suite.test("numeric underflow boundaries", suite::numericUnderflowBoundaries);
        suite.test("AST precedence shape", suite::astPrecedenceShape);
        suite.test("right-associative assignment", suite::rightAssociativeAssignment);
        suite.test("initializer and redeclaration scope rules", suite::initializerAndRedeclaration);
        suite.test("value semantics and rendering", suite::valueSemanticsAndRendering);
        suite.test("dangling else and nearest assignment", suite::controlAndScope);
        suite.test("runtime diagnostic parity", suite::runtimeDiagnosticParity);
        suite.test("semantic execution limit parity", suite::semanticLimitParity);
        suite.test("dense bytecode execution limit parity", suite::denseBytecodeLimitParity);
        suite.test("compiler jump and tick invariants", suite::compilerInvariants);
        suite.test("malformed bytecode matrix", suite::malformedBytecodeMatrix);
        suite.test("cyclic malformed bytecode limit", suite::rawInstructionLimit);
        suite.test("reusable components reset state", suite::reusableComponents);
        suite.test("returned structures are immutable", suite::immutableStructures);
        suite.test("deterministic differential corpus", suite::differentialCorpus);
        System.out.println("reference tests: " + suite.passed + " passed, " + suite.failed + " failed");
        if (suite.failed != 0) System.exit(1);
    }

    private void allTokens() {
        List<TokenType> expected = List.of(
                TokenType.LEFT_PAREN, TokenType.RIGHT_PAREN, TokenType.LEFT_BRACE, TokenType.RIGHT_BRACE,
                TokenType.COMMA, TokenType.MINUS, TokenType.PLUS, TokenType.SEMICOLON, TokenType.SLASH,
                TokenType.STAR, TokenType.BANG, TokenType.BANG_EQUAL, TokenType.EQUAL_EQUAL,
                TokenType.EQUAL, TokenType.GREATER, TokenType.LESS, TokenType.GREATER_EQUAL,
                TokenType.LESS_EQUAL, TokenType.AND, TokenType.ELSE, TokenType.FALSE, TokenType.IF,
                TokenType.LET, TokenType.NIL, TokenType.OR, TokenType.PRINT, TokenType.TRUE,
                TokenType.WHILE, TokenType.IDENTIFIER, TokenType.EOF);
        List<TokenType> actual = Mica.tokenize("(){} ,-+;/* ! != == = > < >= <= "
                + "and else false if let nil or print true while name_2")
                .stream().map(Token::type).toList();
        equal(expected, actual);
    }

    private void commentsAndEofLocation() {
        List<Token> tokens = Mica.tokenize("// ignored symbols != \"x\"\nprint 1;\n");
        equal(List.of(TokenType.PRINT, TokenType.NUMBER, TokenType.SEMICOLON, TokenType.EOF),
                tokens.stream().map(Token::type).toList());
        equal("2:1", tokens.get(0).location());
        equal("3:1", tokens.get(3).location());
    }

    private void stringsAndLexicalFailures() {
        Token string = Mica.tokenize("\"a\\tb\\\"c\\\\d\\n\"").get(0);
        equal("a\tb\"c\\d\n", string.literal());

        locatedFailure("\"bad\\q\"", MicaException.Kind.LEX, 1, 5);
        locatedFailure("\"never closes", MicaException.Kind.LEX, 1, 1);
        locatedFailure("@", MicaException.Kind.LEX, 1, 1);
        locatedFailure("999999999999999999999999999999999999999999999999999999999999999999999999999999"
                + "999999999999999999999999999999999999999999999999999999999999999999999999999999"
                + "999999999999999999999999999999999999999999999999999999999999999999999999999999"
                + "999999999999999999999999999999999999999999999999999999999999999999999999999999;",
                MicaException.Kind.LEX, 1, 1);
    }

    private void numericUnderflowBoundaries() {
        String acceptedMinimum = "0." + "0".repeat(323) + "3";
        equal(Double.MIN_VALUE, Mica.tokenize(acceptedMinimum).get(0).literal());
        equal(0.0, Mica.tokenize("0." + "0".repeat(400)).get(0).literal());

        locatedFailure("0." + "0".repeat(323) + "2", MicaException.Kind.LEX, 1, 1);
        locatedFailure("0." + "0".repeat(400) + "1", MicaException.Kind.LEX, 1, 1);
    }

    private void astPrecedenceShape() {
        Stmt statement = Mica.parse("print 1 + 2 * 3;").get(0);
        check(statement instanceof Stmt.Print, "expected print statement");
        Expr expression = ((Stmt.Print) statement).expression();
        check(expression instanceof Expr.Binary, "expected outer binary expression");
        Expr.Binary plus = (Expr.Binary) expression;
        equal(TokenType.PLUS, plus.operator().type());
        check(plus.right() instanceof Expr.Binary, "expected multiplication on right");
        equal(TokenType.STAR, ((Expr.Binary) plus.right()).operator().type());
    }

    private void rightAssociativeAssignment() {
        parity("let a = 1; let b = 2; print a = b = 9; print a; print b;",
                List.of("9", "9", "9"));
        locatedFailure("(1 + 2) = 3;", MicaException.Kind.PARSE, 1, 9);
    }

    private void initializerAndRedeclaration() {
        parity("let x = 10; { let x = x + 1; print x; } print x;", List.of("11", "10"));
        for (Engine engine : Engine.values()) {
            MicaException error = failure(() -> Mica.run("let x = 1; let x = x + 1;", engine));
            equal(MicaException.Kind.RUNTIME, error.kind());
            equal("1:16", error.line() + ":" + error.column());
        }
    }

    private void valueSemanticsAndRendering() {
        parity("print 1 == \"1\"; print nil == nil; print -0 == 0; print -0;"
                + " print 10000000; print 0.125; print \"x\" + \"y\";",
                List.of("false", "true", "true", "-0", "1E7", "0.125", "xy"));
        diagnosticParity("print 1 + \"x\";", MicaException.Kind.RUNTIME, 1, 9);
        diagnosticParity("print 1 / -0;", MicaException.Kind.RUNTIME, 1, 9);
    }

    private void controlAndScope() {
        parity("if (true) if (false) print 1; else print 2; else print 3;", List.of("2"));
        parity("let x = 1; { { x = 4; } let x = 8; { x = 9; } print x; } print x;",
                List.of("9", "4"));
    }

    private void runtimeDiagnosticParity() {
        diagnosticParity("print absent;", MicaException.Kind.RUNTIME, 1, 7);
        diagnosticParity("absent = 1;", MicaException.Kind.RUNTIME, 1, 1);
        diagnosticParity("print true and 1;", MicaException.Kind.RUNTIME, 1, 12);
        diagnosticParity("if (nil) print 1;", MicaException.Kind.RUNTIME, 1, 1);
        diagnosticParity("print \"a\" < \"b\";", MicaException.Kind.RUNTIME, 1, 11);
    }

    private void semanticLimitParity() {
        MicaException tree = failure(() -> Mica.run("while (true) {}", Engine.TREE));
        MicaException vm = failure(() -> Mica.run("while (true) {}", Engine.VM));
        equal(MicaException.Kind.LIMIT, tree.kind());
        equal(tree.kind(), vm.kind());
        equal("1:14", tree.line() + ":" + tree.column());
        equal(tree.line() + ":" + tree.column(), vm.line() + ":" + vm.column());
    }

    private void denseBytecodeLimitParity() {
        String sum = String.join(" + ", Collections.nCopies(100, "1"));
        String finite = "let i = 0;\nwhile (i < 6000) {\n" + sum
                + ";\ni = i + 1;\n}\nprint i;";
        parity(finite, List.of("6000"));

        String infinite = "let sentinel = 0;\nwhile (true) {\n" + sum + ";\n}";
        MicaException tree = failure(() -> Mica.run(infinite, Engine.TREE));
        MicaException vm = failure(() -> Mica.run(infinite, Engine.VM));
        equal(MicaException.Kind.LIMIT, tree.kind());
        equal(tree.kind(), vm.kind());
        equal(tree.line() + ":" + tree.column(), vm.line() + ":" + vm.column());
        equal(tree.detail(), vm.detail());
    }

    private void compilerInvariants() {
        BytecodeProgram program = Mica.compile("let x = true; if (x and true) { print 1; }"
                + " while (false) print 2;");
        long tickCount = program.code().stream().filter(item -> item.op() == OpCode.TICK).count();
        equal(6L, tickCount);
        for (Instruction instruction : program.code()) {
            if (instruction.op() == OpCode.JUMP || instruction.op() == OpCode.JUMP_IF_FALSE
                    || instruction.op() == OpCode.LOOP) {
                check(instruction.operand() instanceof Integer, "unpatched jump");
                int target = (Integer) instruction.operand();
                check(target >= 0 && target < program.code().size(), "jump outside code");
            }
        }
        equal(List.of("1"), new VirtualMachine().execute(program));
    }

    private void malformedBytecodeMatrix() {
        assertControlled(new BytecodeProgram(List.of(), List.of()));
        assertControlled(new BytecodeProgram(Collections.singletonList(null), List.of()));
        assertControlled(program(new Instruction(null, null, 2, 3)));
        assertControlled(program(new Instruction(OpCode.POP, null, 2, 3)));
        assertControlled(program(new Instruction(OpCode.CONSTANT, "zero", 2, 3)));
        assertControlled(new BytecodeProgram(List.of(new Instruction(OpCode.CONSTANT, 1, 2, 3)), List.of(1.0)));
        assertControlled(new BytecodeProgram(List.of(new Instruction(OpCode.CONSTANT, 0, 2, 3)), List.of(true)));
        assertControlled(program(new Instruction(OpCode.JUMP, 2, 2, 3)));
        assertControlled(program(new Instruction(OpCode.EXIT_SCOPE, null, 2, 3)));
        assertControlled(program(new Instruction(OpCode.TRUE, 7, 2, 3)));
        assertControlled(new BytecodeProgram(List.of(new Instruction(OpCode.TRUE, null, 2, 3),
                new Instruction(OpCode.HALT, null, 2, 4)), List.of()));
        assertControlled(new BytecodeProgram(List.of(new Instruction(OpCode.ENTER_SCOPE, null, 2, 3),
                new Instruction(OpCode.HALT, null, 2, 4)), List.of()));
        assertControlled(new BytecodeProgram(null, List.of()));
        assertControlled(program(new Instruction(OpCode.HALT, null, 0, 1)));

        Instruction halt = new Instruction(OpCode.HALT, null, 7, 8);
        List<Instruction> withNullTail = new ArrayList<>();
        withNullTail.add(halt);
        withNullTail.add(null);
        assertControlled(new BytecodeProgram(withNullTail, List.of()));
        assertControlled(new BytecodeProgram(List.of(halt,
                new Instruction(null, null, 8, 1)), List.of()));
        assertControlled(new BytecodeProgram(List.of(halt,
                new Instruction(OpCode.TRUE, 1, 8, 2)), List.of()));
        assertControlled(new BytecodeProgram(List.of(halt,
                new Instruction(OpCode.CONSTANT, 1, 8, 3)), List.of(1.0)));
        assertControlled(new BytecodeProgram(List.of(halt,
                new Instruction(OpCode.JUMP, 7, 8, 4)), List.of()));
    }

    private void rawInstructionLimit() {
        BytecodeProgram cycle = new BytecodeProgram(
                List.of(new Instruction(OpCode.JUMP, 0, 4, 5)), List.of());
        MicaException error = failure(() -> new VirtualMachine().execute(cycle));
        equal(MicaException.Kind.LIMIT, error.kind());
        equal("4:5", error.line() + ":" + error.column());
    }

    private void reusableComponents() {
        Lexer lexer = new Lexer("print 1;");
        equal(lexer.scanTokens(), lexer.scanTokens());
        Parser parser = new Parser(lexer.scanTokens());
        equal(parser.parse(), parser.parse());

        Interpreter interpreter = new Interpreter();
        equal(List.of("1"), interpreter.execute(Mica.parse("print 1;")));
        equal(List.of("2"), interpreter.execute(Mica.parse("print 2;")));

        BytecodeCompiler compiler = new BytecodeCompiler();
        VirtualMachine vm = new VirtualMachine();
        equal(List.of("3"), vm.execute(compiler.compile(Mica.parse("print 3;"))));
        equal(List.of("4"), vm.execute(compiler.compile(Mica.parse("print 4;"))));
    }

    private void immutableStructures() {
        expectUnsupported(() -> Mica.tokenize("").add(new Token(TokenType.EOF, "", null, 1, 1)));
        expectUnsupported(() -> Mica.parse("print 1;").clear());
        BytecodeProgram program = Mica.compile("print 1;");
        expectUnsupported(() -> program.code().clear());
        expectUnsupported(() -> program.constants().clear());
    }

    private void differentialCorpus() {
        List<String> expressions = List.of(
                "1 + 2 * 3", "(1 + 2) * 3", "8 / 4 / 2", "-3 + 7", "!false",
                "1 < 2 and 3 >= 3", "false or true and false", "nil == nil", "nil != false",
                "\"a\" + \"b\" == \"ab\"", "1 == true", "2 <= 2", "3 > 9", "true or missing",
                "false and (1 / 0 > 2)");
        for (String expression : expressions) compareOutcome("print " + expression + ";");

        List<String> programs = List.of(
                "let x = 0; while (x < 7) { x = x + 1; } print x;",
                "let x = 1; { let y = x + 2; print y; } print x;",
                "if (1 < 2) { print \"yes\"; } else { print \"no\"; }",
                "let x = false; print x or (x = true); print x;",
                "let x = 1; { x = x + 1; { x = x + 1; } } print x;");
        for (String program : programs) compareOutcome(program);
    }

    private static BytecodeProgram program(Instruction first) {
        return new BytecodeProgram(List.of(first, new Instruction(OpCode.HALT, null, 9, 9)), List.of());
    }

    private static void assertControlled(BytecodeProgram program) {
        MicaException error = failure(() -> new VirtualMachine().execute(program));
        check(error.kind() == MicaException.Kind.RUNTIME || error.kind() == MicaException.Kind.LIMIT,
                "unexpected malformed-bytecode error kind");
    }

    private static void parity(String source, List<String> expected) {
        equal(expected, Mica.run(source, Engine.TREE));
        equal(expected, Mica.run(source, Engine.VM));
    }

    private static void diagnosticParity(String source, MicaException.Kind kind, int line, int column) {
        MicaException tree = failure(() -> Mica.run(source, Engine.TREE));
        MicaException vm = failure(() -> Mica.run(source, Engine.VM));
        equal(kind, tree.kind());
        equal(tree.kind(), vm.kind());
        equal(line + ":" + column, tree.line() + ":" + tree.column());
        equal(tree.line() + ":" + tree.column(), vm.line() + ":" + vm.column());
    }

    private static void locatedFailure(String source, MicaException.Kind kind, int line, int column) {
        MicaException error = failure(() -> Mica.run(source, Engine.TREE));
        equal(kind, error.kind());
        equal(line + ":" + column, error.line() + ":" + error.column());
    }

    private static void compareOutcome(String source) {
        equal(outcome(source, Engine.TREE), outcome(source, Engine.VM));
    }

    private static String outcome(String source, Engine engine) {
        try {
            return "OK " + Mica.run(source, engine);
        } catch (MicaException exception) {
            return "ERR " + exception.kind() + " " + exception.line() + ":" + exception.column();
        }
    }

    private void test(String name, CheckedRunnable body) {
        try {
            body.run();
            passed++;
            System.out.println("PASS " + name);
        } catch (Throwable throwable) {
            failed++;
            System.out.println("FAIL " + name + ": " + throwable);
        }
    }

    private static MicaException failure(CheckedRunnable body) {
        try {
            body.run();
        } catch (MicaException exception) {
            return exception;
        }
        throw new AssertionError("expected MicaException");
    }

    private static void expectUnsupported(CheckedRunnable body) {
        try {
            body.run();
            throw new AssertionError("expected immutable structure");
        } catch (UnsupportedOperationException expected) {
            // Expected.
        }
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static void equal(Object expected, Object actual) {
        if (expected == null ? actual != null : !expected.equals(actual)) {
            throw new AssertionError("expected <" + expected + "> but was <" + actual + ">");
        }
    }

    @FunctionalInterface
    private interface CheckedRunnable { void run(); }
}
