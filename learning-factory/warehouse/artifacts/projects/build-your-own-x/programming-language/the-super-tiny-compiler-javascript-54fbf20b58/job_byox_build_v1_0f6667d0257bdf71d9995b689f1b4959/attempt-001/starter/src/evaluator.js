import { PebbleNotImplementedError } from "./errors.js";

export class Evaluator {
  constructor(options = {}) {
    this.options = options;
  }

  evaluate(program) {
    // TODO: walk the AST, maintain one program-wide environment, collect emitted
    // values, enforce types/runtime errors, and account for maxSteps.
    void program;
    throw new PebbleNotImplementedError("tree evaluator");
  }
}
