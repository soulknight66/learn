import { PebbleNotImplementedError } from "./errors.js";

export class Lexer {
  constructor(source) {
    if (typeof source !== "string") {
      throw new TypeError("Pebble source must be a string");
    }

    this.source = source;
  }

  tokenize() {
    // TODO: scan this.source, track one-based locations, skip whitespace/comments,
    // reject malformed input, and append exactly one EOF token.
    throw new PebbleNotImplementedError("tokenizer");
  }
}
