package org.learningfactory.mica;

public record Instruction(OpCode op, Object operand, int line, int column) {
}
