package dev.learningfactory.sprig;

import java.security.MessageDigest;
import java.util.Arrays;
import java.util.HexFormat;

public final class BenchmarkMain {
    private static final int WARMUP = 50;
    private static final int SAMPLES = 200;

    public static void main(String[] args) throws Exception {
        String source = sourceProgram(200);
        for (int i = 0; i < WARMUP; i++) compile(source);

        byte[] baseline = null;
        long start = System.nanoTime();
        for (int i = 0; i < SAMPLES; i++) {
            byte[] current = compile(source);
            if (baseline == null) baseline = current;
            if (!Arrays.equals(baseline, current)) {
                throw new AssertionError("nondeterministic compiler output");
            }
        }
        long elapsed = System.nanoTime() - start;
        String digest = HexFormat.of().formatHex(
                MessageDigest.getInstance("SHA-256").digest(baseline));
        System.out.println("samples=" + SAMPLES);
        System.out.println("elapsed_ns=" + elapsed);
        System.out.println("class_sha256=" + digest);
    }

    private static byte[] compile(String source) {
        CompilationResult result = SprigCompiler.compile(source, "BenchmarkProgram");
        if (!result.succeeded()) throw new AssertionError(result.diagnostics());
        return result.classBytes();
    }

    private static String sourceProgram(int assignments) {
        StringBuilder source = new StringBuilder("fn main() -> Int { let x = 1; ");
        for (int i = 0; i < assignments; i++) source.append("x = x * 3 + 1; ");
        return source.append("return x; }").toString();
    }
}

