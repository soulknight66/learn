package org.learningfactory.mica;

import java.util.List;

public final class MicaPublicTest {
    private int passed;
    private int failed;

    public static void main(String[] args) {
        MicaPublicTest suite = new MicaPublicTest();
        suite.test("scanner locations and escapes", suite::scannerLocationsAndEscapes);
        suite.test("operator precedence on both engines", suite::operatorPrecedence);
        suite.test("lexical shadowing", suite::lexicalShadowing);
        suite.test("loop, assignment, and branch", suite::controlFlow);
        suite.test("short circuit", suite::shortCircuit);
        suite.test("phase and source diagnostics", suite::diagnostics);
        suite.test("bytecode is substantive", suite::bytecodeIsSubstantive);
        suite.test("malformed bytecode is controlled", suite::malformedBytecode);
        suite.test("returned output is immutable", suite::immutableOutput);
        System.out.println("public tests: " + suite.passed + " passed, " + suite.failed + " failed");
        if (suite.failed != 0) System.exit(1);
    }

    private void scannerLocationsAndEscapes() {
        List<Token> tokens = Mica.tokenize("let x=1;\n  print \"a\\n\";");
        equal(TokenType.LET, tokens.get(0).type());
        equal(1, tokens.get(0).line());
        equal(1, tokens.get(0).column());
        equal(TokenType.PRINT, tokens.get(5).type());
        equal(2, tokens.get(5).line());
        equal(3, tokens.get(5).column());
        equal("a\n", tokens.get(6).literal());
        equal(9, tokens.get(6).column());
        equal(TokenType.EOF, tokens.get(tokens.size() - 1).type());
    }

    private void operatorPrecedence() {
        String source = "print 2 + 3 * 4 == 14; print (2 + 3) * 4; print 9 / 2;";
        parity(source, List.of("true", "20", "4.5"));
    }

    private void lexicalShadowing() {
        String source = "let x = \"outer\"; { let x = \"inner\"; print x; } print x;";
        parity(source, List.of("inner", "outer"));
    }

    private void controlFlow() {
        String source = "let n = 1; let sum = 0; while (n <= 5) { sum = sum + n; n = n + 1; }"
                + " if (sum == 15) print sum; else print 0; let a = 0; let b = 0; a = b = 7; print a + b;";
        parity(source, List.of("15", "14"));
    }

    private void shortCircuit() {
        String source = "print true or (1 / 0 > 0); print false and missing;";
        parity(source, List.of("true", "false"));
    }

    private void diagnostics() {
        MicaException lex = failure(() -> Mica.run("print \"x\\q\";", Engine.TREE));
        equal(MicaException.Kind.LEX, lex.kind());
        equal("1:9", lex.line() + ":" + lex.column());

        MicaException parse = failure(() -> Mica.run("1 = 2;", Engine.TREE));
        equal(MicaException.Kind.PARSE, parse.kind());
        equal("1:3", parse.line() + ":" + parse.column());

        for (Engine engine : Engine.values()) {
            MicaException runtime = failure(() -> Mica.run("print 1 / 0;", engine));
            equal(MicaException.Kind.RUNTIME, runtime.kind());
            equal("1:9", runtime.line() + ":" + runtime.column());
        }
    }

    private void bytecodeIsSubstantive() {
        BytecodeProgram program = Mica.compile("print 1 + 2;");
        check(program.code().stream().anyMatch(instruction -> instruction.op() == OpCode.ADD), "missing ADD");
        check(program.code().stream().anyMatch(instruction -> instruction.op() == OpCode.PRINT), "missing PRINT");
        equal(OpCode.HALT, program.code().get(program.code().size() - 1).op());
    }

    private void malformedBytecode() {
        BytecodeProgram bad = new BytecodeProgram(List.of(
                new Instruction(OpCode.POP, null, 3, 4),
                new Instruction(OpCode.HALT, null, 3, 5)), List.of());
        MicaException failure = failure(() -> new VirtualMachine().execute(bad));
        equal(MicaException.Kind.RUNTIME, failure.kind());
        equal("3:4", failure.line() + ":" + failure.column());
    }

    private void immutableOutput() {
        List<String> output = Mica.run("print nil;", Engine.TREE);
        equal(List.of("nil"), output);
        try {
            output.add("changed");
            throw new AssertionError("output list was mutable");
        } catch (UnsupportedOperationException expected) {
            // Expected.
        }
    }

    private static void parity(String source, List<String> expected) {
        equal(expected, Mica.run(source, Engine.TREE));
        equal(expected, Mica.run(source, Engine.VM));
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
