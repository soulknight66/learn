package dev.learningfactory.sprig;

/** Marker types for a suggested immutable abstract syntax tree. */
final class Ast {
    private Ast() { }

    interface Node { }
    interface Statement extends Node { }
    interface Expression extends Node { }
    record Program(java.util.List<Statement> statements) implements Node { }
}

