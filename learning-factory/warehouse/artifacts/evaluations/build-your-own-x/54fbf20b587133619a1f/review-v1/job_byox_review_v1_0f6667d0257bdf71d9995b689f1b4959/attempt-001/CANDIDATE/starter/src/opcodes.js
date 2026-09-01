/** Stable instruction names shared by Pebble's compiler and virtual machine. */
export const OpCode = Object.freeze({
  CONSTANT: "CONSTANT",
  LOAD: "LOAD",
  DEFINE: "DEFINE",
  STORE: "STORE",
  EMIT: "EMIT",
  NEGATE: "NEGATE",
  NOT: "NOT",
  ADD: "ADD",
  SUBTRACT: "SUBTRACT",
  MULTIPLY: "MULTIPLY",
  DIVIDE: "DIVIDE",
  EQUAL: "EQUAL",
  NOT_EQUAL: "NOT_EQUAL",
  LESS: "LESS",
  LESS_EQUAL: "LESS_EQUAL",
  GREATER: "GREATER",
  GREATER_EQUAL: "GREATER_EQUAL",
  JUMP_IF_FALSE: "JUMP_IF_FALSE",
  JUMP: "JUMP",
  HALT: "HALT"
});
