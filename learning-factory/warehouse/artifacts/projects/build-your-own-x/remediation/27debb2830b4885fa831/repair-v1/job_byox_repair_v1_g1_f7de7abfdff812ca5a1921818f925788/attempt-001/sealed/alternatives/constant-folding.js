import { binary, isLanguageValue, unary } from "../reference/src/semantics.js";
import { LanguageError } from "../reference/src/errors.js";

export function foldConstants(ast) {
  if (!ast || typeof ast !== "object") return ast;
  if (Array.isArray(ast)) return ast.map(foldConstants);
  const copy = {};
  for (const [key, value] of Object.entries(ast)) {
    copy[key] = key === "loc" ? { ...value } : foldConstants(value);
  }
  if (copy.type === "UnaryExpression" && copy.argument?.type === "Literal") {
    return attempt(() => unary(copy.operator, copy.argument.value, copy.loc), copy);
  }
  if (copy.type === "BinaryExpression" && copy.left?.type === "Literal" && copy.right?.type === "Literal") {
    return attempt(() => binary(copy.operator, copy.left.value, copy.right.value, copy.loc), copy);
  }
  return copy;
}

function attempt(operation, original) {
  try {
    const value = operation();
    return isLanguageValue(value) ? { type: "Literal", value, loc: { ...original.loc } } : original;
  } catch (error) {
    if (error instanceof LanguageError) return original;
    throw error;
  }
}
