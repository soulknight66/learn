package org.learningfactory.mica;

import java.util.List;

public final class VirtualMachine {
    public static final int EXECUTION_LIMIT = 100_000;

    public List<String> execute(BytecodeProgram program) {
        // TODO(student): validate and execute bytecode with checked stacks, scopes, jumps, and budget.
        int instructionCount = program == null || program.code() == null ? 0 : program.code().size();
        throw new UnsupportedOperationException("TODO(student): VirtualMachine.execute for "
                + instructionCount + " instructions");
    }
}
