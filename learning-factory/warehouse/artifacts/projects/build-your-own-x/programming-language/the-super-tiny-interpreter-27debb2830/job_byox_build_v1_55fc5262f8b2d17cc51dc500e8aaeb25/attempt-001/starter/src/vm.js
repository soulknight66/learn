import { NotImplementedError } from "./errors.js";

export function runBytecode(program, options = {}) {
  void program;
  void options;
  // TODO: validate all bytecode before dispatch, then execute within fixed limits.
  throw new NotImplementedError("runBytecode");
}
