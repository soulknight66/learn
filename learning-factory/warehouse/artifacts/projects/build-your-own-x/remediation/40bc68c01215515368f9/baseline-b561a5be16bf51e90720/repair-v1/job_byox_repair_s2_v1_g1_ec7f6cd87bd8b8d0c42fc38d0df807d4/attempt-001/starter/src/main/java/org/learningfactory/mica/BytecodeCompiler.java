package org.learningfactory.mica;

import java.util.List;

public final class BytecodeCompiler {
    public BytecodeProgram compile(List<Stmt> statements) {
        // TODO(student): emit stack-machine instructions and patch all forward control-flow targets.
        int statementCount = statements == null ? 0 : statements.size();
        throw new UnsupportedOperationException("TODO(student): BytecodeCompiler.compile for "
                + statementCount + " statements");
    }
}
