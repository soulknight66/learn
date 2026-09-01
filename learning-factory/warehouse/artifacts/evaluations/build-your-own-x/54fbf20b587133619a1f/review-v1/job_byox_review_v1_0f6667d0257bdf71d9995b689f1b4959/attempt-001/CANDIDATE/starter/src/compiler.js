import { PebbleNotImplementedError } from "./errors.js";

export class Compiler {
  compile(program) {
    // TODO: lower the documented AST to the deterministic bytecode envelope and
    // OpCode instruction contract documented in ../README.md.
    void program;
    throw new PebbleNotImplementedError("bytecode compiler");
  }
}
