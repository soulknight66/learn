package dev.learningfactory.sprig;

final class CompileFailure extends Exception {
    private static final long serialVersionUID = 1L;
    private final Diagnostic diagnostic;

    private CompileFailure(Diagnostic diagnostic) {
        super(diagnostic.message());
        this.diagnostic = diagnostic;
    }

    static CompileFailure at(String code, int line, int column, String message) {
        return new CompileFailure(new Diagnostic(code, line, column, message));
    }

    static CompileFailure at(String code, Ast.Pos pos, String message) {
        return at(code, pos.line(), pos.column(), message);
    }

    Diagnostic diagnostic() {
        return diagnostic;
    }
}
