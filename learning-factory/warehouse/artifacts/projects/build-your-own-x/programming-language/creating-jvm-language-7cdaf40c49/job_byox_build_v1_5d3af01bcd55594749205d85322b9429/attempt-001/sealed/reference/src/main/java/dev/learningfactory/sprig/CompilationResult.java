package dev.learningfactory.sprig;

import java.util.List;
import java.util.Objects;

public final class CompilationResult {
    private final byte[] classBytes;
    private final List<Diagnostic> diagnostics;

    private CompilationResult(byte[] classBytes, List<Diagnostic> diagnostics) {
        this.classBytes = classBytes.clone();
        this.diagnostics = List.copyOf(diagnostics);
    }

    public static CompilationResult success(byte[] bytes) {
        Objects.requireNonNull(bytes, "bytes");
        if (bytes.length == 0) throw new IllegalArgumentException("empty class bytes");
        return new CompilationResult(bytes, List.of());
    }

    public static CompilationResult failure(List<Diagnostic> diagnostics) {
        Objects.requireNonNull(diagnostics, "diagnostics");
        if (diagnostics.isEmpty()) throw new IllegalArgumentException("missing diagnostic");
        return new CompilationResult(new byte[0], diagnostics);
    }

    public boolean succeeded() {
        return diagnostics.isEmpty();
    }

    public byte[] classBytes() {
        return classBytes.clone();
    }

    public List<Diagnostic> diagnostics() {
        return diagnostics;
    }
}

