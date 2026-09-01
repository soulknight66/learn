import { NotImplementedError } from "./errors.js";

export function interpret(ast, options = {}) {
  void ast;
  void options;
  // TODO: evaluate with lexical environments and a deterministic step budget.
  throw new NotImplementedError("interpret");
}
