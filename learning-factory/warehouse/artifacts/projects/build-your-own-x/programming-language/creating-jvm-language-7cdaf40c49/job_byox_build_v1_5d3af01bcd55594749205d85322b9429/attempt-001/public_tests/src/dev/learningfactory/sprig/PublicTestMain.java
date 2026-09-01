package dev.learningfactory.sprig;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

public final class PublicTestMain {
    private static int checks;

    public static void main(String[] args) throws Exception {
        compilesAndRunsArithmetic();
        honorsPrecedence();
        executesControlFlowAndPrint();
        rejectsBadClassName();
        rejectsTypeMismatch();
        isDeterministicAndDefensive();
        System.out.println("public checks passed: " + checks);
    }

    private static void compilesAndRunsArithmetic() throws Exception {
        String source = "fn main() -> Int { let x = 40; return x + 2; }";
        CompilationResult result = requireSuccess(source, "ArithmeticProgram");
        byte[] bytes = result.classBytes();
        check(bytes.length >= 4, "class output is not empty");
        check((bytes[0] & 255) == 0xca && (bytes[1] & 255) == 0xfe
                && (bytes[2] & 255) == 0xba && (bytes[3] & 255) == 0xbe,
                "class-file magic");
        check(run(bytes) == 42, "local arithmetic evaluates to 42");
    }

    private static void honorsPrecedence() throws Exception {
        String source = "fn main() -> Int { return 2 + 3 * 4 - 5; }";
        check(run(requireSuccess(source, "PrecedenceProgram").classBytes()) == 9,
                "multiplication binds tighter than addition");
    }

    private static void executesControlFlowAndPrint() throws Exception {
        String source = "fn main() -> Int { let n = 4; let sum = 0; "
                + "while (n > 0) { if (n == 2) { sum = sum + 10; } else { "
                + "sum = sum + n; } n = n - 1; } print sum; return sum; }";
        CompilationResult result = requireSuccess(source, "FlowProgram");
        PrintStream previous = System.out;
        ByteArrayOutputStream captured = new ByteArrayOutputStream();
        int value;
        try {
            System.setOut(new PrintStream(captured, true, StandardCharsets.UTF_8));
            value = run(result.classBytes());
        } finally {
            System.setOut(previous);
        }
        check(value == 18, "while and if compute expected result");
        check(captured.toString(StandardCharsets.UTF_8).trim().equals("18"),
                "print writes the integer");
    }

    private static void rejectsBadClassName() {
        CompilationResult result = SprigCompiler.compile(
                "fn main() -> Int { return 0; }", "bad/name");
        check(!result.succeeded(), "bad class name fails");
        check(result.diagnostics().stream().anyMatch(d -> d.code().equals("E_CLASS_NAME")),
                "bad class name has stable code");
    }

    private static void rejectsTypeMismatch() {
        CompilationResult result = SprigCompiler.compile(
                "fn main() -> Int { let x = true; return x; }", "BadTypes");
        check(!result.succeeded(), "type mismatch fails");
        check(result.diagnostics().stream().anyMatch(d -> d.code().equals("E_TYPE")),
                "type mismatch has stable code");
    }

    private static void isDeterministicAndDefensive() {
        String source = "fn main() -> Int { return 7; }";
        CompilationResult first = requireSuccess(source, "Repeatable");
        CompilationResult second = requireSuccess(source, "Repeatable");
        byte[] original = first.classBytes();
        byte[] mutated = first.classBytes();
        mutated[0] = 0;
        check(Arrays.equals(original, first.classBytes()), "result returns defensive copies");
        check(Arrays.equals(original, second.classBytes()), "class bytes are deterministic");
    }

    private static CompilationResult requireSuccess(String source, String name) {
        CompilationResult result = SprigCompiler.compile(source, name);
        if (!result.succeeded()) {
            throw new AssertionError("expected success, got " + result.diagnostics());
        }
        return result;
    }

    private static int run(byte[] bytes) throws Exception {
        Class<?> generated = new ByteLoader().define(bytes);
        Method method = generated.getMethod("run");
        try {
            return (Integer) method.invoke(null);
        } catch (InvocationTargetException e) {
            Throwable cause = e.getCause();
            if (cause instanceof Exception exception) throw exception;
            if (cause instanceof Error error) throw error;
            throw e;
        }
    }

    private static void check(boolean condition, String label) {
        checks++;
        if (!condition) throw new AssertionError(label);
    }

    private static final class ByteLoader extends ClassLoader {
        Class<?> define(byte[] bytes) {
            return defineClass(null, bytes, 0, bytes.length);
        }
    }
}
