import { PebbleNotImplementedError } from "./errors.js";

export class VirtualMachine {
  constructor(options = {}) {
    this.options = options;
  }

  execute(bytecode) {
    // TODO: validate/execute the documented bytecode envelope and OpCode set,
    // collect emitted values, enforce runtime errors, and account for maxSteps.
    void bytecode;
    throw new PebbleNotImplementedError("virtual machine");
  }
}
