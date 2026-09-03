import { MicaRuntimeError } from "./diagnostics.mjs";
import { applyBinary, applyUnary, formatValue, isMicaValue, isTruthy } from "./runtime.mjs";

const NO_ARG_OPS = new Set([
  "NEGATE", "NOT", "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "EQUAL", "NOT_EQUAL",
  "LESS", "LESS_EQUAL", "GREATER", "GREATER_EQUAL", "PRINT", "POP", "ENTER_SCOPE",
  "EXIT_SCOPE", "HALT",
]);
const NAME_OPS = new Set(["LOAD", "DEFINE", "STORE"]);
const JUMP_OPS = new Set(["JUMP_IF_FALSE", "JUMP"]);
const BINARY_OPERATORS = Object.freeze({
  ADD: "+",
  SUBTRACT: "-",
  MULTIPLY: "*",
  DIVIDE: "/",
  EQUAL: "==",
  NOT_EQUAL: "!=",
  LESS: "<",
  LESS_EQUAL: "<=",
  GREATER: ">",
  GREATER_EQUAL: ">=",
});

function invalid(message, span = null) {
  throw new MicaRuntimeError("E_INVALID_BYTECODE", message, span);
}

function isArray(value) {
  try {
    return Array.isArray(value);
  } catch {
    return false;
  }
}

function isRecord(value) {
  return value !== null && typeof value === "object" && !isArray(value);
}

function readOwnData(record, key, context) {
  let descriptor;
  try {
    descriptor = Object.getOwnPropertyDescriptor(record, key);
  } catch {
    invalid(`${context} is not an inspectable inert data record`);
  }
  if (descriptor === undefined || !Object.hasOwn(descriptor, "value")) {
    invalid(`${context} must define '${key}' as an own data property`);
  }
  return descriptor.value;
}

function copyDataArray(value, context) {
  if (!isArray(value)) invalid(`${context} must be an array`);
  const length = readOwnData(value, "length", context);
  const copy = [];
  for (let index = 0; index < length; index += 1) {
    copy.push(readOwnData(value, String(index), `${context} entry ${index}`));
  }
  return copy;
}

function validatePosition(position, context) {
  if (!isRecord(position)) invalid(`${context} must be a position record`);
  const offset = readOwnData(position, "offset", context);
  const line = readOwnData(position, "line", context);
  const column = readOwnData(position, "column", context);
  if (!Number.isSafeInteger(offset) || offset < 0) {
    invalid(`${context} has an invalid offset`);
  }
  if (!Number.isSafeInteger(line) || line < 1) {
    invalid(`${context} has an invalid line`);
  }
  if (!Number.isSafeInteger(column) || column < 1) {
    invalid(`${context} has an invalid column`);
  }
  return { offset, line, column };
}

function validateSpan(value, instructionIndex) {
  if (value === null) return null;
  const context = `instruction ${instructionIndex} span`;
  if (!isRecord(value)) invalid(`${context} must be null or a span record`);
  const start = validatePosition(readOwnData(value, "start", context), `${context} start`);
  const end = validatePosition(readOwnData(value, "end", context), `${context} end`);
  if (
    end.offset < start.offset ||
    end.line < start.line ||
    (end.line === start.line && end.column < start.column)
  ) {
    invalid(`${context} end precedes its start`);
  }
  return { start, end };
}

function validateChunk(chunk) {
  if (!isRecord(chunk)) invalid("chunk must be an inert data record");
  const constants = copyDataArray(readOwnData(chunk, "constants", "chunk"), "chunk constants");
  const instructions = copyDataArray(readOwnData(chunk, "code", "chunk"), "chunk code");
  if (instructions.length === 0) invalid("chunk contains no instructions");
  for (const constant of constants) {
    if (!isMicaValue(constant)) invalid("constant is not a Mica value");
  }
  const code = instructions.map((instruction, index) => {
    if (!isRecord(instruction)) invalid(`instruction ${index} must be an inert data record`);
    const op = readOwnData(instruction, "op", `instruction ${index}`);
    const arg = readOwnData(instruction, "arg", `instruction ${index}`);
    const span = validateSpan(readOwnData(instruction, "span", `instruction ${index}`), index);
    if (typeof op !== "string") {
      invalid(`instruction ${index} opcode must be a string`, span);
    }
    if (op === "CONSTANT") {
      if (!Number.isInteger(arg) || arg < 0 || arg >= constants.length) {
        invalid(`instruction ${index} has an invalid constant index`, span);
      }
    } else if (NAME_OPS.has(op)) {
      if (typeof arg !== "string" || !/^[A-Za-z_][A-Za-z0-9_]*$/.test(arg)) {
        invalid(`instruction ${index} has an invalid name operand`, span);
      }
    } else if (JUMP_OPS.has(op)) {
      if (!Number.isInteger(arg) || arg < 0 || arg >= instructions.length) {
        invalid(`instruction ${index} has an invalid jump target`, span);
      }
    } else if (NO_ARG_OPS.has(op)) {
      if (arg !== null) invalid(`instruction ${index} should not have an operand`, span);
    } else {
      invalid(`instruction ${index} has an unknown opcode`, span);
    }
    return { op, arg, span };
  });
  return { constants, code };
}

export function run(chunk) {
  const { constants, code } = validateChunk(chunk);
  const stack = [];
  const scopes = [new Map()];
  const output = [];
  let programCounter = 0;
  let steps = 0;
  const stepLimit = Math.max(1024, code.length * 64);

  const pop = (span) => {
    if (stack.length === 0) invalid("operand stack underflow", span);
    return stack.pop();
  };
  const peek = (span) => {
    if (stack.length === 0) invalid("operand stack underflow", span);
    return stack.at(-1);
  };
  const findScope = (name) => {
    for (let index = scopes.length - 1; index >= 0; index -= 1) {
      if (scopes[index].has(name)) return scopes[index];
    }
    return null;
  };

  while (true) {
    steps += 1;
    if (steps > stepLimit) invalid("instruction limit exceeded");
    if (programCounter < 0 || programCounter >= code.length) {
      invalid("program counter left the chunk");
    }
    const instruction = code[programCounter];
    programCounter += 1;
    const { op, arg, span = null } = instruction;

    if (op === "CONSTANT") {
      stack.push(constants[arg]);
    } else if (op === "LOAD") {
      const scope = findScope(arg);
      if (scope === null) {
        throw new MicaRuntimeError("E_UNDEFINED_NAME", `undefined name '${arg}'`, span);
      }
      stack.push(scope.get(arg));
    } else if (op === "DEFINE") {
      const scope = scopes.at(-1);
      if (scope.has(arg)) {
        throw new MicaRuntimeError("E_DUPLICATE_BINDING", `duplicate binding '${arg}'`, span);
      }
      scope.set(arg, pop(span));
    } else if (op === "STORE") {
      const scope = findScope(arg);
      if (scope === null) {
        throw new MicaRuntimeError("E_UNDEFINED_NAME", `undefined name '${arg}'`, span);
      }
      scope.set(arg, peek(span));
    } else if (op === "NEGATE" || op === "NOT") {
      const value = pop(span);
      stack.push(applyUnary(op === "NEGATE" ? "-" : "!", value, span));
    } else if (Object.hasOwn(BINARY_OPERATORS, op)) {
      const right = pop(span);
      const left = pop(span);
      stack.push(applyBinary(BINARY_OPERATORS[op], left, right, span));
    } else if (op === "PRINT") {
      output.push(formatValue(pop(span)));
    } else if (op === "POP") {
      pop(span);
    } else if (op === "ENTER_SCOPE") {
      scopes.push(new Map());
    } else if (op === "EXIT_SCOPE") {
      if (scopes.length === 1) invalid("cannot exit global scope", span);
      scopes.pop();
    } else if (op === "JUMP_IF_FALSE") {
      if (!isTruthy(pop(span))) programCounter = arg;
    } else if (op === "JUMP") {
      programCounter = arg;
    } else if (op === "HALT") {
      if (scopes.length !== 1) invalid("unbalanced lexical scopes at HALT", span);
      if (stack.length !== 1) invalid("HALT requires exactly one result value", span);
      return { value: pop(span), output };
    }
  }
}
