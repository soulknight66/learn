import { BYTECODE_FORMAT, BYTECODE_VERSION, OpCode } from "./compiler.js";
import { BytecodeError, RuntimeError, StepLimitError } from "./errors.js";
import {
  applyBinary,
  applyUnary,
  readMaxSteps,
  requireBoolean,
} from "./runtime-values.js";

export const DEFAULT_MAX_STEPS = 10_000;

const IDENTIFIER = /^[A-Za-z_][A-Za-z0-9_]*$/;
const NO_OPERAND = new Set([
  OpCode.EMIT,
  OpCode.NEGATE,
  OpCode.NOT,
  OpCode.ADD,
  OpCode.SUBTRACT,
  OpCode.MULTIPLY,
  OpCode.DIVIDE,
  OpCode.EQUAL,
  OpCode.NOT_EQUAL,
  OpCode.LESS,
  OpCode.LESS_EQUAL,
  OpCode.GREATER,
  OpCode.GREATER_EQUAL,
  OpCode.HALT,
]);
const NAME_OPERAND = new Set([OpCode.LOAD, OpCode.DEFINE, OpCode.STORE]);
const TARGET_OPERAND = new Set([OpCode.JUMP, OpCode.JUMP_IF_FALSE]);
const BINARY_OPERATOR = Object.freeze({
  [OpCode.ADD]: "+",
  [OpCode.SUBTRACT]: "-",
  [OpCode.MULTIPLY]: "*",
  [OpCode.DIVIDE]: "/",
  [OpCode.EQUAL]: "==",
  [OpCode.NOT_EQUAL]: "!=",
  [OpCode.LESS]: "<",
  [OpCode.LESS_EQUAL]: "<=",
  [OpCode.GREATER]: ">",
  [OpCode.GREATER_EQUAL]: ">=",
});

function hasExactKeys(value, expected) {
  const actual = Reflect.ownKeys(value);
  if (actual.some((key) => typeof key !== "string")) return false;
  actual.sort();
  return actual.length === expected.length
    && actual.every((key, index) => key === [...expected].sort()[index]);
}

function validateBytecode(bytecode) {
  if (bytecode === null || typeof bytecode !== "object" || Array.isArray(bytecode)) {
    throw new BytecodeError("bytecode must be an object");
  }
  if (!hasExactKeys(bytecode, ["format", "version", "constants", "instructions"])) {
    throw new BytecodeError("bytecode has invalid top-level fields");
  }
  if (bytecode.format !== BYTECODE_FORMAT || bytecode.version !== BYTECODE_VERSION) {
    throw new BytecodeError("unsupported bytecode format or version");
  }
  if (!Array.isArray(bytecode.constants)) {
    throw new BytecodeError("bytecode constants must be an array");
  }
  for (let index = 0; index < bytecode.constants.length; index += 1) {
    const value = bytecode.constants[index];
    if (typeof value !== "boolean" && (typeof value !== "number" || !Number.isFinite(value))) {
      throw new BytecodeError(`constant ${index} must be a finite number or boolean`);
    }
  }
  if (!Array.isArray(bytecode.instructions) || bytecode.instructions.length === 0) {
    throw new BytecodeError("bytecode instructions must be a non-empty array");
  }

  const instructions = bytecode.instructions;
  for (let pc = 0; pc < instructions.length; pc += 1) {
    const instruction = instructions[pc];
    if (instruction === null || typeof instruction !== "object" || Array.isArray(instruction)) {
      throw new BytecodeError(`instruction ${pc} must be an object`);
    }
    const { op } = instruction;
    if (typeof op !== "string") throw new BytecodeError(`instruction ${pc} has no opcode`);

    if (op === OpCode.CONSTANT) {
      if (!hasExactKeys(instruction, ["op", "arg"])) {
        throw new BytecodeError(`instruction ${pc} has invalid operands`);
      }
      if (!Number.isInteger(instruction.arg)
          || instruction.arg < 0
          || instruction.arg >= bytecode.constants.length) {
        throw new BytecodeError(`instruction ${pc} has an invalid constant index`);
      }
      continue;
    }

    if (NAME_OPERAND.has(op)) {
      if (!hasExactKeys(instruction, ["op", "arg"])
          || typeof instruction.arg !== "string"
          || !IDENTIFIER.test(instruction.arg)) {
        throw new BytecodeError(`instruction ${pc} has an invalid name operand`);
      }
      continue;
    }

    if (TARGET_OPERAND.has(op)) {
      if (!hasExactKeys(instruction, ["op", "arg"])
          || !Number.isInteger(instruction.arg)
          || instruction.arg < 0
          || instruction.arg >= instructions.length) {
        throw new BytecodeError(`instruction ${pc} has an invalid jump target`);
      }
      continue;
    }

    if (NO_OPERAND.has(op)) {
      if (!hasExactKeys(instruction, ["op"])) {
        throw new BytecodeError(`instruction ${pc} has unexpected operands`);
      }
      if (op === OpCode.HALT && pc !== instructions.length - 1) {
        throw new BytecodeError("HALT must be the final instruction");
      }
      continue;
    }

    throw new BytecodeError(`instruction ${pc} has unknown opcode '${op}'`);
  }

  if (instructions.at(-1).op !== OpCode.HALT) {
    throw new BytecodeError("bytecode must end with HALT");
  }
  return instructions;
}

/** Execute validated Pebble stack bytecode. */
export function execute(bytecode, options = {}) {
  const instructions = validateBytecode(bytecode);
  const maxSteps = readMaxSteps(options, DEFAULT_MAX_STEPS);
  const variables = new Map();
  const stack = [];
  const output = [];
  let pc = 0;
  let steps = 0;

  const pop = (op) => {
    if (stack.length === 0) throw new BytecodeError(`stack underflow at instruction ${pc} (${op})`);
    return stack.pop();
  };

  while (true) {
    if (steps >= maxSteps) {
      throw new StepLimitError(`step limit exceeded (${maxSteps})`);
    }
    const instruction = instructions[pc];
    const instructionPc = pc;
    steps += 1;

    switch (instruction.op) {
      case OpCode.CONSTANT:
        stack.push(bytecode.constants[instruction.arg]);
        pc += 1;
        break;
      case OpCode.LOAD:
        if (!variables.has(instruction.arg)) {
          throw new RuntimeError(`undefined variable '${instruction.arg}'`, "UNDEFINED_VARIABLE");
        }
        stack.push(variables.get(instruction.arg));
        pc += 1;
        break;
      case OpCode.DEFINE: { // Match interpreter order: consume the value before name validation.
        const value = pop(instruction.op);
        if (variables.has(instruction.arg)) {
          throw new RuntimeError(`duplicate variable '${instruction.arg}'`, "DUPLICATE_VARIABLE");
        }
        variables.set(instruction.arg, value);
        pc += 1;
        break;
      }
      case OpCode.STORE: {
        const value = pop(instruction.op);
        if (!variables.has(instruction.arg)) {
          throw new RuntimeError(`undefined variable '${instruction.arg}'`, "UNDEFINED_VARIABLE");
        }
        variables.set(instruction.arg, value);
        pc += 1;
        break;
      }
      case OpCode.EMIT:
        output.push(pop(instruction.op));
        pc += 1;
        break;
      case OpCode.NEGATE:
        stack.push(applyUnary("-", pop(instruction.op)));
        pc += 1;
        break;
      case OpCode.NOT:
        stack.push(applyUnary("!", pop(instruction.op)));
        pc += 1;
        break;
      case OpCode.ADD:
      case OpCode.SUBTRACT:
      case OpCode.MULTIPLY:
      case OpCode.DIVIDE:
      case OpCode.EQUAL:
      case OpCode.NOT_EQUAL:
      case OpCode.LESS:
      case OpCode.LESS_EQUAL:
      case OpCode.GREATER:
      case OpCode.GREATER_EQUAL: { // Left is below right on the stack.
        const right = pop(instruction.op);
        const left = pop(instruction.op);
        stack.push(applyBinary(BINARY_OPERATOR[instruction.op], left, right));
        pc += 1;
        break;
      }
      case OpCode.JUMP_IF_FALSE: {
        const condition = pop(instruction.op);
        requireBoolean(condition, "condition");
        pc = condition ? pc + 1 : instruction.arg;
        break;
      }
      case OpCode.JUMP:
        pc = instruction.arg;
        break;
      case OpCode.HALT:
        if (stack.length !== 0) {
          throw new BytecodeError(`non-empty stack at instruction ${instructionPc} (HALT)`);
        }
        return output;
      default:
        throw new BytecodeError(`unreachable invalid opcode at instruction ${instructionPc}`);
    }
  }
}
