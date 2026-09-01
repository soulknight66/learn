package dev.learningfactory.sprig;

import java.util.List;

/** Public facade for the Sprig compiler. */
public final class SprigCompiler {
    private SprigCompiler() { }

    public static CompilationResult compile(String source, String className) {
        if (source == null || className == null) {
            throw new NullPointerException("source and className are required");
        }

        // TODO: validate className, then connect Lexer, Parser, Analyzer, and
        // ClassEmitter. Convert expected CompileFailure values to diagnostics.
        return CompilationResult.failure(List.of(new Diagnostic(
                "E_NOT_IMPLEMENTED", 1, 1, "complete the Sprig compiler")));
    }
}

