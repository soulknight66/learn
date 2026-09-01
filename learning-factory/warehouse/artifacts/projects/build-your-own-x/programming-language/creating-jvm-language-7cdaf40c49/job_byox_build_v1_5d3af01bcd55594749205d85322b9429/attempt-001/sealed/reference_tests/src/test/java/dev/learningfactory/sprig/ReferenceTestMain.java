package dev.learningfactory.sprig;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

public final class ReferenceTestMain {
    private static int checks;

    public static void main(String[] args) throws Exception {
        arithmeticAndLocals();
        precedenceAndUnary();
        comparisonsAndLogic();
        shortCircuiting();
        loopsBranchesAndPrinting();
        pathSensitiveDeclarations();
        classArtifactContract();
        runtimeArithmeticFailure();
        lexicalDiagnostics();
        syntaxAndSemanticDiagnostics();
        nestingLimit();
        System.out.println("sealed reference checks passed: " + checks);
    }

    private static void arithmeticAndLocals() throws Exception {
        String source = program("let x = 9; let y = 4; x = x + 1; "
                + "return x * y + x / y + x % y;");
        check(run(success(source, "Arithmetic")) == 44, "arithmetic and assignment");
        check(run(success(program("return 2147483647 + 1;"), "Overflow"))
                == Integer.MIN_VALUE, "JVM integer overflow semantics");
    }

    private static void precedenceAndUnary() throws Exception {
        check(run(success(program("return 20 - 3 - 2 * 4;"), "Precedence")) == 9,
                "left associativity and precedence");
        check(run(success(program("return -(-5);"), "Unary")) == 5,
                "nested arithmetic unary");
    }

    private static void comparisonsAndLogic() throws Exception {
        String body = "if ((2 < 3 && 3 <= 3) && (4 > 3 && 4 >= 4) "
                + "&& (true == !false) && (2 != 3)) { return 1; } else { return 0; }";
        check(run(success(program(body), "Comparisons")) == 1,
                "comparisons and canonical booleans");
        check(run(success(program("if (false || true) { return 8; } else { return 9; }"),
                "LogicalOr")) == 8, "logical OR");
    }

    private static void shortCircuiting() throws Exception {
        String andSource = program("if (false && (1 / 0 == 0)) { return 0; } "
                + "else { return 11; }");
        String orSource = program("if (true || (1 / 0 == 0)) { return 12; } "
                + "else { return 0; }");
        check(run(success(andSource, "ShortAnd")) == 11, "AND skips right operand");
        check(run(success(orSource, "ShortOr")) == 12, "OR skips right operand");
    }

    private static void loopsBranchesAndPrinting() throws Exception {
        String source = program("let n = 5; let sum = 0; while (n > 0) { "
                + "if (n == 3) { sum = sum + 20; } else { sum = sum + n; } "
                + "n = n - 1; } print sum; return sum;");
        byte[] bytes = success(source, "FlowAndPrint");
        PrintStream previous = System.out;
        ByteArrayOutputStream captured = new ByteArrayOutputStream();
        int value;
        try {
            System.setOut(new PrintStream(captured, true, StandardCharsets.UTF_8));
            value = run(bytes);
        } finally {
            System.setOut(previous);
        }
        check(value == 32, "loop and branches");
        check(captured.toString(StandardCharsets.UTF_8).trim().equals("32"),
                "print output");
    }

    private static void pathSensitiveDeclarations() throws Exception {
        String valid = program("if (true) { return 1; } else { let x = 2; } return x;");
        check(run(success(valid, "TerminatingPath")) == 1,
                "declaration needed only on continuing paths");
        expectCode(program("if (true) { let x = 1; } else { } return x;"),
                "PathMissing", "E_UNDECLARED");
        expectCode(program("while (false) { let x = 1; } return x;"),
                "LoopMissing", "E_UNDECLARED");
    }

    private static void classArtifactContract() throws Exception {
        String source = program("return 70000;");
        CompilationResult first = SprigCompiler.compile(source, "Artifact");
        CompilationResult second = SprigCompiler.compile(source, "Artifact");
        require(first.succeeded(), "artifact compiles");
        byte[] bytes = first.classBytes();
        check((bytes[0] & 255) == 0xca && (bytes[1] & 255) == 0xfe
                && (bytes[2] & 255) == 0xba && (bytes[3] & 255) == 0xbe,
                "class magic");
        int major = (bytes[6] & 255) << 8 | bytes[7] & 255;
        check(major == 49, "class major version 49");
        check(Arrays.equals(bytes, second.classBytes()), "deterministic bytes");
        byte[] changed = first.classBytes();
        changed[0] = 0;
        check(Arrays.equals(bytes, first.classBytes()), "defensive class-byte copy");
        check(run(bytes) == 70000, "ldc_w constant");
        expectCode(source, "bad/name", "E_CLASS_NAME");
        expectCode(source, "", "E_CLASS_NAME");
    }

    private static void runtimeArithmeticFailure() throws Exception {
        byte[] bytes = success(program("let z = 0; return 5 / z;"), "DivideZero");
        try {
            run(bytes);
            throw new AssertionError("division by zero should throw");
        } catch (ArithmeticException expected) {
            check(true, "division by zero preserves JVM exception");
        }
    }

    private static void lexicalDiagnostics() {
        expectDiagnostic("fn main() -> Int {\r\n  @\r\n}", "BadChar",
                "E_CHAR", 2, 3);
        expectCode(program("return 2147483648;"), "LargeInteger", "E_INT_RANGE");
        expectCode(program("return 01;"), "LeadingZero", "E_SYNTAX");
        expectCode(program("if (true & false) { return 1; } else { return 0; }"),
                "LoneAmpersand", "E_CHAR");
    }

    private static void syntaxAndSemanticDiagnostics() {
        expectCode("fn main() -> Int { return 1 }", "MissingSemicolon", "E_SYNTAX");
        expectCode(program("let x = x + 1; return 0;"), "SelfReference", "E_UNDECLARED");
        expectCode(program("let x = 1; let x = 2; return x;"), "Duplicate", "E_DUPLICATE");
        expectCode(program("let x = true; return x;"), "WrongReturn", "E_TYPE");
        expectCode(program("if (1) { return 1; } else { return 2; }"),
                "WrongCondition", "E_TYPE");
        expectCode(program("let x = 1;"), "NoReturn", "E_MISSING_RETURN");
        expectCode(program("return 1; print 2;"), "DeadCode", "E_UNREACHABLE");
        expectCode(program("x = 1; return 0;"), "UnknownAssignment", "E_UNDECLARED");
    }

    private static void nestingLimit() {
        StringBuilder source = new StringBuilder("fn main() -> Int { return ");
        source.append("(".repeat(257));
        source.append('1');
        source.append(")".repeat(257));
        source.append("; }");
        expectCode(source.toString(), "TooDeep", "E_LIMIT");
    }

    private static String program(String body) {
        return "fn main() -> Int { " + body + " }";
    }

    private static byte[] success(String source, String className) {
        CompilationResult result = SprigCompiler.compile(source, className);
        if (!result.succeeded()) {
            throw new AssertionError("expected success but got " + result.diagnostics());
        }
        return result.classBytes();
    }

    private static void expectCode(String source, String className, String code) {
        CompilationResult result = SprigCompiler.compile(source, className);
        require(!result.succeeded(), "expected failure " + code);
        check(result.diagnostics().get(0).code().equals(code),
                "diagnostic code " + code + ", got " + result.diagnostics());
        check(result.classBytes().length == 0, "failure has no class bytes");
    }

    private static void expectDiagnostic(String source, String className, String code,
            int line, int column) {
        CompilationResult result = SprigCompiler.compile(source, className);
        require(!result.succeeded(), "expected located failure");
        Diagnostic diagnostic = result.diagnostics().get(0);
        check(diagnostic.code().equals(code), "located diagnostic code");
        check(diagnostic.line() == line && diagnostic.column() == column,
                "located diagnostic position, got " + diagnostic);
    }

    private static int run(byte[] bytes) throws Exception {
        Class<?> generated = new ByteLoader().define(bytes);
        Method run = generated.getMethod("run");
        try {
            return (Integer) run.invoke(null);
        } catch (InvocationTargetException wrapper) {
            Throwable cause = wrapper.getCause();
            if (cause instanceof Exception exception) throw exception;
            if (cause instanceof Error error) throw error;
            throw wrapper;
        }
    }

    private static void check(boolean condition, String label) {
        checks++;
        if (!condition) throw new AssertionError(label);
    }

    private static void require(boolean condition, String label) {
        if (!condition) throw new AssertionError(label);
    }

    private static final class ByteLoader extends ClassLoader {
        Class<?> define(byte[] bytes) {
            return defineClass(null, bytes, 0, bytes.length);
        }
    }
}
