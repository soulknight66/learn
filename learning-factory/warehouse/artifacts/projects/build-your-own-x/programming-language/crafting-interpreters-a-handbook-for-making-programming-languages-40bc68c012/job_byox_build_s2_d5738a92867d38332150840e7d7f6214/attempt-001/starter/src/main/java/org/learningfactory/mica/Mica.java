package org.learningfactory.mica;

import java.util.List;

public final class Mica {
    private Mica() { }

    public static List<Token> tokenize(String source) { return new Lexer(source).scanTokens(); }

    public static List<Stmt> parse(String source) { return new Parser(tokenize(source)).parse(); }

    public static BytecodeProgram compile(String source) { return new BytecodeCompiler().compile(parse(source)); }

    public static List<String> run(String source, Engine engine) {
        if (engine == null) throw new MicaException(MicaException.Kind.RUNTIME, 1, 1, "engine must not be null");
        List<Stmt> statements = parse(source);
        return switch (engine) {
            case TREE -> new Interpreter().execute(statements);
            case VM -> new VirtualMachine().execute(new BytecodeCompiler().compile(statements));
        };
    }
}
