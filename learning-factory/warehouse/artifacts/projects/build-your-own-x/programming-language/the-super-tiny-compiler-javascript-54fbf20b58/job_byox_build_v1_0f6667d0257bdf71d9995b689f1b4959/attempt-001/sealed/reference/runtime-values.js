import { RuntimeError } from "./errors.js";

export function requireNumber(value, operator) {
  if (typeof value !== "number") {
    throw new RuntimeError(`operator '${operator}' requires number operands`, "TYPE_ERROR");
  }
  return value;
}

export function requireBoolean(value, context) {
  if (typeof value !== "boolean") {
    throw new RuntimeError(`${context} requires a boolean`, "TYPE_ERROR");
  }
  return value;
}

export function applyUnary(operator, value) {
  if (operator === "-") return -requireNumber(value, operator);
  if (operator === "!") return !requireBoolean(value, "operator '!'");
  throw new RuntimeError(`unknown unary operator '${operator}'`, "TYPE_ERROR");
}

export function applyBinary(operator, left, right) {
  if (operator === "==") return left === right;
  if (operator === "!=") return left !== right;

  requireNumber(left, operator);
  requireNumber(right, operator);

  switch (operator) {
    case "+": return left + right;
    case "-": return left - right;
    case "*": return left * right;
    case "/":
      if (right === 0) throw new RuntimeError("division by zero", "DIVISION_BY_ZERO");
      return left / right;
    case "<": return left < right;
    case "<=": return left <= right;
    case ">": return left > right;
    case ">=": return left >= right;
    default: throw new RuntimeError(`unknown binary operator '${operator}'`, "TYPE_ERROR");
  }
}

export function readMaxSteps(options, fallback = 10_000) {
  if (options === undefined) options = {};
  if (options === null || typeof options !== "object" || Array.isArray(options)) {
    throw new RuntimeError("options must be an object", "INVALID_OPTIONS");
  }
  for (const key of Reflect.ownKeys(options)) {
    if (key !== "maxSteps") {
      throw new RuntimeError(`unknown option '${String(key)}'`, "INVALID_OPTIONS");
    }
  }
  const maxSteps = options.maxSteps === undefined ? fallback : options.maxSteps;
  if (!Number.isSafeInteger(maxSteps) || maxSteps <= 0) {
    throw new RuntimeError("maxSteps must be a positive safe integer", "INVALID_OPTIONS");
  }
  return maxSteps;
}
