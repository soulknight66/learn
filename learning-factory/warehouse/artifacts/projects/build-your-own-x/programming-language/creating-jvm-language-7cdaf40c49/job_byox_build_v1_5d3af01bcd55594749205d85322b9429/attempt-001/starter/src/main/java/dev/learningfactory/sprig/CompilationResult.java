package dev.learningfactory.sprig;

import java.util.List;
import java.util.Objects;

/** Immutable success-or-diagnostics result for one compilation. */
public final class CompilationResult {
    private final byte[] classBytes;
    private final List<Diagnostic> diagnostics;

    private CompilationResult(byte[] classBytes, List<Diagnostic> diagnostics) {
        this.classBytes = classBytes.clone();
        this.diagnostics = List.copyOf(diagnostics);
    }

    public static CompilationResult success(byte[] classBytes) {
        Objects.requireNonNull(classBytes, "classBytes");
        if (classBytes.length == 0) {
            throw new IllegalArgumentException("successful output must not be empty");
        }
        return new CompilationResult(classBytes, List.of());
    }

    public static CompilationResult failure(List<Diagnostic> diagnostics) {
        Objects.requireNonNull(diagnostics, "diagnostics");
        if (diagnostics.isEmpty()) {
            throw new IllegalArgumentException("failure requires a diagnostic");
        }
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

