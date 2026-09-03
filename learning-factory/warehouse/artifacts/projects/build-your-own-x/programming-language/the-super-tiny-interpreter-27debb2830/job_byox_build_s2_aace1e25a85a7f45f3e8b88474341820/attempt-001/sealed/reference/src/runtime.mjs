import { MicaRuntimeError } from "./diagnostics.mjs";

export function isMicaValue(value) {
  return (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean" ||
    (typeof value === "number" && Number.isFinite(value))
  );
}

export function isTruthy(value) {
  return value !== false && value !== null;
}

export function formatValue(value) {
  if (value === null) return "nil";
  if (value === true) return "true";
  if (value === false) return "false";
  return String(value);
}

function runtimeError(code, message, span) {
  throw new MicaRuntimeError(code, message, span ?? null);
}

function requireNumber(value, operator, span) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    runtimeError("E_TYPE", `operator '${operator}' expects number operands`, span);
  }
  return value;
}

function finiteResult(value, span) {
  if (!Number.isFinite(value)) runtimeError("E_NUMBER_RANGE", "numeric result is not finite", span);
  return value;
}

export function applyUnary(operator, value, span) {
  if (operator === "!") return !isTruthy(value);
  if (operator === "-") return finiteResult(-requireNumber(value, operator, span), span);
  runtimeError("E_INVALID_OPERATOR", `unknown unary operator '${operator}'`, span);
}

export function applyBinary(operator, left, right, span) {
  switch (operator) {
    case "+":
      if (typeof left === "string" && typeof right === "string") return left + right;
      if (typeof left === "number" && typeof right === "number") {
        return finiteResult(left + right, span);
      }
      runtimeError("E_TYPE", "operator '+' expects two numbers or two strings", span);
      break;
    case "-":
      return finiteResult(
        requireNumber(left, operator, span) - requireNumber(right, operator, span),
        span,
      );
    case "*":
      return finiteResult(
        requireNumber(left, operator, span) * requireNumber(right, operator, span),
        span,
      );
    case "/": {
      const numerator = requireNumber(left, operator, span);
      const denominator = requireNumber(right, operator, span);
      if (denominator === 0) runtimeError("E_DIV_ZERO", "division by zero", span);
      return finiteResult(numerator / denominator, span);
    }
    case "==": return typeof left === typeof right && left === right;
    case "!=": return !(typeof left === typeof right && left === right);
    case "<":
      return requireNumber(left, operator, span) < requireNumber(right, operator, span);
    case "<=":
      return requireNumber(left, operator, span) <= requireNumber(right, operator, span);
    case ">":
      return requireNumber(left, operator, span) > requireNumber(right, operator, span);
    case ">=":
      return requireNumber(left, operator, span) >= requireNumber(right, operator, span);
    default:
      runtimeError("E_INVALID_OPERATOR", `unknown binary operator '${operator}'`, span);
  }
}
