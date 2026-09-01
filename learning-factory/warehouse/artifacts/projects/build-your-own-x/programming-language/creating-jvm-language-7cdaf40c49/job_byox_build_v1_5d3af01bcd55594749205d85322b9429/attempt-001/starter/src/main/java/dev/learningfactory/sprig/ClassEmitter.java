package dev.learningfactory.sprig;

/** Suggested dependency-free JVM class-file backend. */
final class ClassEmitter {
    byte[] emit(Ast.Program program, String className) throws CompileFailure {
        throw CompileFailure.at("E_NOT_IMPLEMENTED", 1, 1,
                "implement class-file emission");
    }
}

