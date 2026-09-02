package org.learningfactory.mica;

import java.util.List;

public final class Interpreter {
    public static final int EXECUTION_LIMIT = 100_000;

    public List<String> execute(List<Stmt> statements) {
        // TODO(student): evaluate AST nodes with nested Environment instances and a statement budget.
        int statementCount = statements == null ? 0 : statements.size();
        throw new UnsupportedOperationException("TODO(student): Interpreter.execute for " + statementCount + " statements");
    }
}
