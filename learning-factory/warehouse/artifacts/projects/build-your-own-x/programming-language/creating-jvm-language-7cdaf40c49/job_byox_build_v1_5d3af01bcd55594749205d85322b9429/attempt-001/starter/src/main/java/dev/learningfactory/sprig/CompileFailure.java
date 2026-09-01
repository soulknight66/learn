package dev.learningfactory.sprig;

/** Internal expected failure; the public facade converts it to result data. */
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

    Diagnostic diagnostic() {
        return diagnostic;
    }
}
