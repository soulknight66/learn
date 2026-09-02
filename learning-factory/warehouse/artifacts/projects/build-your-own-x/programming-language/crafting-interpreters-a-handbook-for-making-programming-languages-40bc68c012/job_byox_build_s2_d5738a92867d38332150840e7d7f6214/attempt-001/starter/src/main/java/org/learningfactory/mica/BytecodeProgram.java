package org.learningfactory.mica;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public record BytecodeProgram(List<Instruction> code, List<Object> constants) {
    public BytecodeProgram {
        code = code == null ? null : Collections.unmodifiableList(new ArrayList<>(code));
        constants = constants == null ? null : Collections.unmodifiableList(new ArrayList<>(constants));
    }
}
