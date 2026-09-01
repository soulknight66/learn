package dev.learningfactory.sprig;

/** Suggested type, scope, local-slot, and return-analysis stage. */
final class Analyzer {
    void analyze(Ast.Program program) throws CompileFailure {
        throw CompileFailure.at("E_NOT_IMPLEMENTED", 1, 1,
                "implement static analysis");
    }
}

