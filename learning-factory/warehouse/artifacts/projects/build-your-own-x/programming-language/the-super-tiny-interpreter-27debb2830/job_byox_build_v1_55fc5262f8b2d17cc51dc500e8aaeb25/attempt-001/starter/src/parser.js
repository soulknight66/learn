import { NotImplementedError } from "./errors.js";

export function parse(tokens, options = {}) {
  void tokens;
  void options;
  // TODO: implement the precedence ladder and recursive-depth accounting.
  throw new NotImplementedError("parse");
}
