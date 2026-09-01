/** Base class for errors intentionally exposed by Pebble. */
export class PebbleError extends Error {
  constructor(message, { code = "PEBBLE_ERROR", line = null, column = null } = {}) {
    super(message);
    this.name = new.target.name;
    this.code = code;

    if (line !== null) this.line = line;
    if (column !== null) this.column = column;
  }
}

/** Source text or token stream does not conform to Pebble's grammar. */
export class PebbleSyntaxError extends PebbleError {
  constructor(message, details = {}) {
    super(message, { ...details, code: details.code ?? "SYNTAX_ERROR" });
  }
}

/** A well-formed program performed an invalid operation. */
export class PebbleRuntimeError extends PebbleError {
  constructor(message, details = {}) {
    super(message, { ...details, code: details.code ?? "RUNTIME_ERROR" });
  }
}

/** Execution consumed its configured work budget. */
export class PebbleStepLimitError extends PebbleRuntimeError {
  constructor(message = "Pebble execution exceeded maxSteps", details = {}) {
    super(message, { ...details, code: "STEP_LIMIT_EXCEEDED" });
  }
}

/** Temporary marker used by this intentionally incomplete starter. */
export class PebbleNotImplementedError extends PebbleError {
  constructor(stage) {
    super(`TODO: implement Pebble ${stage}`, { code: "NOT_IMPLEMENTED" });
  }
}
