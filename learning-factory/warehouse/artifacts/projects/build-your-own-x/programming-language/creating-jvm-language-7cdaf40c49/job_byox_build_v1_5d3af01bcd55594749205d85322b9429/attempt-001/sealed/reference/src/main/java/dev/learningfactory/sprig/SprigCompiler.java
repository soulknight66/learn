package dev.learningfactory.sprig;

import java.util.List;
import java.util.Objects;

public final class SprigCompiler {
    private SprigCompiler() { }

    public static CompilationResult compile(String source, String className) {
        Objects.requireNonNull(source, "source");
        Objects.requireNonNull(className, "className");
        if (!validClassName(className)) {
            return CompilationResult.failure(List.of(new Diagnostic(
                    "E_CLASS_NAME", 1, 1,
                    "class name must be a simple ASCII JVM identifier of at most 128 characters")));
        }
        try {
            List<Token> tokens = new Lexer(source).scan();
            Ast.Program program = new Parser(tokens).parse();
            Analyzer.Analysis analysis = new Analyzer().analyze(program);
            byte[] bytes = new ClassEmitter(className, analysis).emit(program);
            return CompilationResult.success(bytes);
        } catch (CompileFailure failure) {
            return CompilationResult.failure(List.of(failure.diagnostic()));
        }
    }

    private static boolean validClassName(String name) {
        if (name.isEmpty() || name.length() > 128) return false;
        if (!identifierStart(name.charAt(0))) return false;
        for (int i = 1; i < name.length(); i++) {
            char c = name.charAt(i);
            if (!identifierStart(c) && (c < '0' || c > '9')) return false;
        }
        return true;
    }

    private static boolean identifierStart(char c) {
        return c == '_' || c == '$' || c >= 'A' && c <= 'Z' || c >= 'a' && c <= 'z';
    }
}

