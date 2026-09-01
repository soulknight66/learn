import { PebbleNotImplementedError } from "./errors.js";

export class Parser {
  constructor(tokens) {
    if (!Array.isArray(tokens)) {
      throw new TypeError("Pebble tokens must be an array");
    }

    this.tokens = tokens;
  }

  parse() {
    // TODO: parse all statements into the AST shapes documented in ../README.md.
    // A precedence-based recursive-descent parser is one suitable design.
    throw new PebbleNotImplementedError("parser");
  }
}
