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

function validateChunk(chunk) {
  if (chunk === null || typeof chunk !== "object") invalid("chunk must be an object");
  if (!Array.isArray(chunk.constants) || !Array.isArray(chunk.code)) {
    invalid("chunk must contain constants and code arrays");
  }
  if (chunk.code.length === 0) invalid("chunk contains no instructions");
  for (const constant of chunk.constants) {
    if (!isMicaValue(constant)) invalid("constant is not a Mica value");
  }
  for (let index = 0; index < chunk.code.length; index += 1) {
    const instruction = chunk.code[index];
    if (instruction === null || typeof instruction !== "object") {
      invalid(`instruction ${index} is not an object`);
    }
    const { op, arg, span = null } = instruction;
    if (op === "CONSTANT") {
      if (!Number.isInteger(arg) || arg < 0 || arg >= chunk.constants.length) {
        invalid(`instruction ${index} has an invalid constant index`, span);
      }
    } else if (NAME_OPS.has(op)) {
      if (typeof arg !== "string" || !/^[A-Za-z_][A-Za-z0-9_]*$/.test(arg)) {
        invalid(`instruction ${index} has an invalid name operand`, span);
      }
    } else if (JUMP_OPS.has(op)) {
      if (!Number.isInteger(arg) || arg < 0 || arg >= chunk.code.length) {
        invalid(`instruction ${index} has an invalid jump target`, span);
      }
    } else if (NO_ARG_OPS.has(op)) {
      if (arg !== null) invalid(`instruction ${index} should not have an operand`, span);
    } else {
      invalid(`instruction ${index} has unknown opcode '${op}'`, span);
    }
  }
}

export function run(chunk) {
  validateChunk(chunk);
  const stack = [];
  const scopes = [new Map()];
  const output = [];
  let programCounter = 0;
  let steps = 0;
  const stepLimit = Math.max(1024, chunk.code.length * 64);

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
    if (programCounter < 0 || programCounter >= chunk.code.length) {
      invalid("program counter left the chunk");
    }
    const instruction = chunk.code[programCounter];
    programCounter += 1;
    const { op, arg, span = null } = instruction;

    if (op === "CONSTANT") {
      stack.push(chunk.constants[arg]);
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
