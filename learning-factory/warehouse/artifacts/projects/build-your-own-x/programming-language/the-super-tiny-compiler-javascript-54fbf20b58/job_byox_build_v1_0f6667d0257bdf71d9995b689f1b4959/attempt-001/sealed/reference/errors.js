/** Base class for every language-defined Pebble failure. */
export class PebbleError extends Error {
  constructor(message, location = undefined, code = "PEBBLE_ERROR") {
    const suffix = location && Number.isInteger(location.line)
      ? ` at ${location.line}:${location.column}`
      : "";
    super(`${message}${suffix}`);
    this.name = new.target.name;
    this.code = code;
    if (location && Number.isInteger(location.line)) {
      this.line = location.line;
      this.column = location.column;
    }
  }
}

export class PebbleSyntaxError extends PebbleError {
  constructor(message, location = undefined, code = "UNEXPECTED_TOKEN") {
    super(message, location, code);
  }
}

export class LexerError extends PebbleSyntaxError {
  constructor(message, location = undefined, code = "UNEXPECTED_CHARACTER") {
    super(message, location, code);
  }
}

export class ParseError extends PebbleSyntaxError {
  constructor(message, location = undefined, code = "UNEXPECTED_TOKEN") {
    super(message, location, code);
  }
}

export class PebbleRuntimeError extends PebbleError {
  constructor(message, code = "RUNTIME_ERROR") {
    super(message, undefined, code);
  }
}

// Short compatibility name used internally and convenient for callers.
export { PebbleRuntimeError as RuntimeError };

export class CompileError extends PebbleError {
  constructor(message, code = "INVALID_AST") {
    super(message, undefined, code);
  }
}

export class BytecodeError extends PebbleRuntimeError {
  constructor(message) {
    super(message, "INVALID_BYTECODE");
  }
}

export class PebbleStepLimitError extends PebbleRuntimeError {
  constructor(message) {
    super(message, "STEP_LIMIT_EXCEEDED");
  }
}

export { PebbleStepLimitError as StepLimitError };
