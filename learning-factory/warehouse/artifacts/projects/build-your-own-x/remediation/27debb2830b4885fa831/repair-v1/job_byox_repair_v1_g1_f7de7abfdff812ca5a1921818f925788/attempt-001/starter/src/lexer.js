import { NotImplementedError } from "./errors.js";

export function tokenize(source, options = {}) {
  void source;
  void options;
  // TODO: scan without regular-expression backtracking and preserve one-based locations.
  throw new NotImplementedError("tokenize");
}
