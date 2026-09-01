import { BytecodeError, RuntimeError, boundedInteger } from "./errors.js";
import { binary, formatValue, isLanguageValue, isTruthy, unary } from "./semantics.js";

const MAX_STEPS = 100_000;
const MAX_INSTRUCTIONS = 500_000;
const MAX_CONSTANTS = 200_000;
const MAX_STACK = 10_000;
const MAX_SCOPES = 1_000;

const PUSH_OPS = new Set(["CONSTANT", "NULL", "TRUE", "FALSE", "GET"]);
const UNARY_OPS = new Set(["NEGATE", "NOT"]);
const BINARY_OPS = new Set([
  "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "EQUAL", "NOT_EQUAL",
  "GREATER", "GREATER_EQUAL", "LESS", "LESS_EQUAL"
]);
const NAME_OPS = new Set(["GET", "DEFINE", "SET"]);
const JUMP_OPS = new Set(["JUMP", "JUMP_IF_FALSE"]);
const NO_ARG_OPS = new Set([
  "NULL", "TRUE", "FALSE", "POP", "PRINT", "NEGATE", "NOT", "ADD", "SUBTRACT",
  "MULTIPLY", "DIVIDE", "EQUAL", "NOT_EQUAL", "GREATER", "GREATER_EQUAL", "LESS",
  "LESS_EQUAL", "ENTER_SCOPE", "EXIT_SCOPE", "HALT"
]);
const ALL_OPS = new Set(["CONSTANT", ...NAME_OPS, ...JUMP_OPS, ...NO_ARG_OPS]);

export function runBytecode(program, options = {}) {
  const limits = {
    steps: boundedInteger(options, "maxSteps", MAX_STEPS),
    instructions: boundedInteger(options, "maxInstructions", MAX_INSTRUCTIONS),
    constants: boundedInteger(options, "maxConstants", MAX_CONSTANTS),
    stack: boundedInteger(options, "maxStack", MAX_STACK),
    scopes: boundedInteger(options, "maxScopes", MAX_SCOPES)
  };
  validateBytecode(program, limits);
  return executeValidated(program, limits.steps);
}

export function validateBytecode(program, limits = {
  instructions: MAX_INSTRUCTIONS,
  constants: MAX_CONSTANTS,
  stack: MAX_STACK,
  scopes: MAX_SCOPES
}) {
  if (!isRecord(program)) throw new BytecodeError("Bytecode program must be a plain object");
  requireExactKeys(program, ["version", "constants", "code"], "bytecode program");
  if (program.version !== 1) throw new BytecodeError("Unsupported bytecode version");
  if (!Array.isArray(program.constants)) throw new BytecodeError("constants must be an array");
  if (!Array.isArray(program.code)) throw new BytecodeError("code must be an array");
  if (program.constants.length > limits.constants) {
    throw new BytecodeError(`Constant count exceeds ${limits.constants}`);
  }
  if (program.code.length === 0) throw new BytecodeError("code must not be empty");
  if (program.code.length > limits.instructions) {
    throw new BytecodeError(`Instruction count exceeds ${limits.instructions}`);
  }
  requireDenseDataArray(program.constants, "constants");
  requireDenseDataArray(program.code, "code");
  for (let i = 0; i < program.constants.length; i += 1) {
    if (!isLanguageValue(program.constants[i])) {
      throw new BytecodeError(`Invalid constant at index ${i}`);
    }
  }
  for (let i = 0; i < program.code.length; i += 1) {
    validateInstruction(program.code[i], i, program.constants.length, program.code.length);
  }
  if (program.code[program.code.length - 1].op !== "HALT") {
    throw new BytecodeError("Final instruction must be HALT");
  }
  for (let i = 0; i + 1 < program.code.length; i += 1) {
    if (program.code[i].op === "HALT") {
      throw new BytecodeError("HALT may appear only as the final instruction", program.code[i].loc);
    }
  }
  validateControlFlow(program.code, limits);
}

function validateInstruction(instruction, index, constantCount, codeLength) {
  if (!isRecord(instruction)) throw new BytecodeError(`Instruction ${index} must be a plain object`);
  const allowedKeys = Object.prototype.hasOwnProperty.call(instruction, "arg")
    ? ["op", "arg", "loc"] : ["op", "loc"];
  requireExactKeys(instruction, allowedKeys, `instruction ${index}`);
  if (typeof instruction.op !== "string" || !ALL_OPS.has(instruction.op)) {
    throw new BytecodeError(`Unknown opcode at instruction ${index}`, validLocation(instruction.loc) ? instruction.loc : undefined);
  }
  if (!validLocation(instruction.loc)) {
    throw new BytecodeError(`Invalid location at instruction ${index}`);
  }
  const hasArg = Object.prototype.hasOwnProperty.call(instruction, "arg");
  if (NO_ARG_OPS.has(instruction.op) && hasArg) {
    throw new BytecodeError(`${instruction.op} forbids an argument`, instruction.loc);
  }
  if (!NO_ARG_OPS.has(instruction.op) && !hasArg) {
    throw new BytecodeError(`${instruction.op} requires an argument`, instruction.loc);
  }
  if (instruction.op === "CONSTANT" &&
      (!Number.isSafeInteger(instruction.arg) || instruction.arg < 0 || instruction.arg >= constantCount)) {
    throw new BytecodeError("CONSTANT index is out of range", instruction.loc);
  }
  if (NAME_OPS.has(instruction.op) &&
      (typeof instruction.arg !== "string" || !/^[A-Za-z_][A-Za-z0-9_]*$/.test(instruction.arg))) {
    throw new BytecodeError(`${instruction.op} requires an identifier argument`, instruction.loc);
  }
  if (JUMP_OPS.has(instruction.op) &&
      (!Number.isSafeInteger(instruction.arg) || instruction.arg < 0 || instruction.arg >= codeLength)) {
    throw new BytecodeError(`${instruction.op} target is out of range`, instruction.loc);
  }
}

function validateControlFlow(code, limits) {
  const states = new Map([[0, { stack: 0, scopes: 1 }]]);
  const queue = [0];
  let head = 0;
  let haltReached = false;
  while (head < queue.length) {
    const ip = queue[head++];
    const before = states.get(ip);
    const instruction = code[ip];
    const after = transfer(instruction, before, limits);
    if (instruction.op === "HALT") {
      haltReached = true;
      continue;
    }
    const successors = instruction.op === "JUMP"
      ? [instruction.arg]
      : instruction.op === "JUMP_IF_FALSE"
        ? [ip + 1, instruction.arg]
        : [ip + 1];
    for (const successor of new Set(successors)) {
      if (successor < 0 || successor >= code.length) {
        throw new BytecodeError("Control flow falls outside code", instruction.loc);
      }
      const known = states.get(successor);
      if (!known) {
        states.set(successor, after);
        queue.push(successor);
      } else if (known.stack !== after.stack || known.scopes !== after.scopes) {
        throw new BytecodeError("Control-flow join has inconsistent stack or scope depth", code[successor].loc);
      }
    }
  }
  if (!haltReached) {
    throw new BytecodeError("Final HALT is unreachable", code[code.length - 1].loc);
  }
}

function transfer(instruction, before, limits) {
  let { stack, scopes } = before;
  const need = (count) => {
    if (stack < count) throw new BytecodeError("Static stack underflow", instruction.loc);
  };
  if (PUSH_OPS.has(instruction.op)) stack += 1;
  else if (instruction.op === "POP") { need(1); stack -= 1; }
  else if (instruction.op === "DEFINE" || instruction.op === "SET" ||
           instruction.op === "PRINT" || UNARY_OPS.has(instruction.op) ||
           instruction.op === "JUMP_IF_FALSE") need(1);
  else if (BINARY_OPS.has(instruction.op)) { need(2); stack -= 1; }
  else if (instruction.op === "ENTER_SCOPE") scopes += 1;
  else if (instruction.op === "EXIT_SCOPE") {
    if (scopes <= 1) throw new BytecodeError("Static scope underflow", instruction.loc);
    scopes -= 1;
  } else if (instruction.op === "HALT") {
    if (stack !== 1 || scopes !== 1) {
      throw new BytecodeError("HALT requires one value and global scope", instruction.loc);
    }
  }
  if (stack > limits.stack) throw new BytecodeError(`Stack depth exceeds ${limits.stack}`, instruction.loc);
  if (scopes > limits.scopes) throw new BytecodeError(`Scope depth exceeds ${limits.scopes}`, instruction.loc);
  return { stack, scopes };
}

function executeValidated(program, maxSteps) {
  const stack = [];
  const scopes = [new Map()];
  const output = [];
  let ip = 0;
  let steps = 0;

  const lookup = (name, loc) => {
    for (let i = scopes.length - 1; i >= 0; i -= 1) {
      if (scopes[i].has(name)) return scopes[i].get(name);
    }
    throw new RuntimeError(`Undefined variable '${name}'`, loc);
  };
  const assign = (name, value, loc) => {
    for (let i = scopes.length - 1; i >= 0; i -= 1) {
      if (scopes[i].has(name)) { scopes[i].set(name, value); return value; }
    }
    throw new RuntimeError(`Undefined variable '${name}'`, loc);
  };

  while (true) {
    const instruction = program.code[ip];
    steps += 1;
    if (steps > maxSteps) {
      throw new RuntimeError(`Execution step limit ${maxSteps} exceeded`, instruction.loc);
    }
    switch (instruction.op) {
      case "CONSTANT": stack.push(program.constants[instruction.arg]); break;
      case "NULL": stack.push(null); break;
      case "TRUE": stack.push(true); break;
      case "FALSE": stack.push(false); break;
      case "GET": stack.push(lookup(instruction.arg, instruction.loc)); break;
      case "DEFINE": {
        const scope = scopes.at(-1);
        if (scope.has(instruction.arg)) {
          throw new RuntimeError(`Variable '${instruction.arg}' is already defined`, instruction.loc);
        }
        scope.set(instruction.arg, stack.at(-1));
        break;
      }
      case "SET": assign(instruction.arg, stack.at(-1), instruction.loc); break;
      case "POP": stack.pop(); break;
      case "PRINT": output.push(formatValue(stack.at(-1))); break;
      case "NEGATE": stack.push(unary("-", stack.pop(), instruction.loc)); break;
      case "NOT": stack.push(unary("!", stack.pop(), instruction.loc)); break;
      case "ADD": applyBinary(stack, "+", instruction.loc); break;
      case "SUBTRACT": applyBinary(stack, "-", instruction.loc); break;
      case "MULTIPLY": applyBinary(stack, "*", instruction.loc); break;
      case "DIVIDE": applyBinary(stack, "/", instruction.loc); break;
      case "EQUAL": applyBinary(stack, "==", instruction.loc); break;
      case "NOT_EQUAL": applyBinary(stack, "!=", instruction.loc); break;
      case "GREATER": applyBinary(stack, ">", instruction.loc); break;
      case "GREATER_EQUAL": applyBinary(stack, ">=", instruction.loc); break;
      case "LESS": applyBinary(stack, "<", instruction.loc); break;
      case "LESS_EQUAL": applyBinary(stack, "<=", instruction.loc); break;
      case "JUMP": ip = instruction.arg; continue;
      case "JUMP_IF_FALSE":
        if (!isTruthy(stack.at(-1))) { ip = instruction.arg; continue; }
        break;
      case "ENTER_SCOPE": scopes.push(new Map()); break;
      case "EXIT_SCOPE": scopes.pop(); break;
      case "HALT": return { value: stack.at(-1), output: [...output] };
      default: throw new BytecodeError("Validated program contains an unknown opcode", instruction.loc);
    }
    ip += 1;
  }
}

function applyBinary(stack, operator, loc) {
  const right = stack.pop();
  const left = stack.pop();
  stack.push(binary(operator, left, right, loc));
}

function isRecord(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function validLocation(value) {
  return isRecord(value) && hasExactDataKeys(value, ["line", "column"]) &&
    Number.isSafeInteger(value.line) && value.line >= 1 &&
    Number.isSafeInteger(value.column) && value.column >= 1;
}

function requireExactKeys(object, expected, label) {
  if (!hasExactDataKeys(object, expected)) {
    throw new BytecodeError(`${label} has unexpected or missing fields`);
  }
}

function hasExactDataKeys(object, expected) {
  const actual = Reflect.ownKeys(object);
  const wanted = [...expected].sort();
  if (actual.some((key) => typeof key !== "string")) return false;
  actual.sort();
  if (actual.length !== wanted.length || actual.some((key, index) => key !== wanted[index])) return false;
  return wanted.every((key) => {
    const descriptor = Object.getOwnPropertyDescriptor(object, key);
    return descriptor && Object.prototype.hasOwnProperty.call(descriptor, "value");
  });
}

function requireDenseDataArray(array, label) {
  if (Object.getPrototypeOf(array) !== Array.prototype) {
    throw new BytecodeError(`${label} must use the intrinsic Array prototype`);
  }
  const keys = Reflect.ownKeys(array);
  if (keys.length !== array.length + 1 || !keys.includes("length")) {
    throw new BytecodeError(`${label} must be a dense array without extra fields`);
  }
  for (let index = 0; index < array.length; index += 1) {
    const descriptor = Object.getOwnPropertyDescriptor(array, String(index));
    if (!descriptor || !Object.prototype.hasOwnProperty.call(descriptor, "value")) {
      throw new BytecodeError(`${label} must contain only data elements`);
    }
  }
}
