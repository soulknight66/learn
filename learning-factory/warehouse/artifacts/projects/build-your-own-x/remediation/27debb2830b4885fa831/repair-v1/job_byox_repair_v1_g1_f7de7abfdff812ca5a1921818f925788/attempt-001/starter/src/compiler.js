import { NotImplementedError } from "./errors.js";

export function compile(ast, options = {}) {
  void ast;
  void options;
  // TODO: preserve one-result-per-statement stack invariants across control flow.
  throw new NotImplementedError("compile");
}
