import { PebbleNotImplementedError } from "./errors.js";

export class VirtualMachine {
  constructor(options = {}) {
    this.options = options;
  }

  execute(bytecode) {
    // TODO: validate/execute the documented bytecode envelope and OpCode set,
    // collect emitted values, reject non-finite numeric results, enforce runtime
    // errors, and charge maxSteps once per dispatched instruction.
    void bytecode;
    throw new PebbleNotImplementedError("virtual machine");
  }
}
