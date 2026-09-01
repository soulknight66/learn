import { RuntimeError } from "./errors.js";

export function isLanguageValue(value) {
  return value === null || typeof value === "string" || typeof value === "boolean" ||
    (typeof value === "number" && Number.isFinite(value));
}

export function isTruthy(value) { return value !== false && value !== null; }

export function formatValue(value) {
  if (value === null) return "null";
  return String(value);
}

export function unary(operator, value, loc) {
  if (operator === "!") return !isTruthy(value);
  if (operator === "-") {
    requireNumber(value, "Unary '-'", loc);
    return -value;
  }
  throw new RuntimeError(`Unknown unary operator ${JSON.stringify(operator)}`, loc);
}

export function binary(operator, left, right, loc) {
  switch (operator) {
    case "+":
      if (typeof left === "number" && typeof right === "number") return finiteResult(left + right, loc);
      if (typeof left === "string" && typeof right === "string") return left + right;
      throw new RuntimeError("'+' requires two numbers or two strings", loc);
    case "-": requireNumbers(left, right, "'-'", loc); return finiteResult(left - right, loc);
    case "*": requireNumbers(left, right, "'*'", loc); return finiteResult(left * right, loc);
    case "/":
      requireNumbers(left, right, "'/'", loc);
      if (right === 0) throw new RuntimeError("Division by zero", loc);
      return finiteResult(left / right, loc);
    case ">": requireNumbers(left, right, "'>'", loc); return left > right;
    case ">=": requireNumbers(left, right, "'>='", loc); return left >= right;
    case "<": requireNumbers(left, right, "'<'", loc); return left < right;
    case "<=": requireNumbers(left, right, "'<='", loc); return left <= right;
    case "==": return typeof left === typeof right && left === right;
    case "!=": return !(typeof left === typeof right && left === right);
    default: throw new RuntimeError(`Unknown binary operator ${JSON.stringify(operator)}`, loc);
  }
}

function finiteResult(value, loc) {
  if (!Number.isFinite(value)) throw new RuntimeError("Numeric result is not finite", loc);
  return value;
}

function requireNumber(value, label, loc) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new RuntimeError(`${label} requires a number`, loc);
  }
}

function requireNumbers(left, right, label, loc) {
  if (typeof left !== "number" || !Number.isFinite(left) ||
      typeof right !== "number" || !Number.isFinite(right)) {
    throw new RuntimeError(`${label} requires two numbers`, loc);
  }
}
