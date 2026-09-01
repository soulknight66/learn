export class LanguageError extends Error {
  constructor(message, stage, location = {}) {
    const line = Number.isInteger(location.line) ? location.line : null;
    const column = Number.isInteger(location.column) ? location.column : null;
    const suffix = line === null ? "" : ` at ${line}:${column}`;
    super(`${message}${suffix}`);
    this.name = new.target.name;
    this.stage = stage;
    this.line = line;
    this.column = column;
  }
}

export class LexError extends LanguageError {
  constructor(message, location) { super(message, "lex", location); }
}

export class ParseError extends LanguageError {
  constructor(message, location) { super(message, "parse", location); }
}

export class RuntimeError extends LanguageError {
  constructor(message, location) { super(message, "runtime", location); }
}

export class CompileError extends LanguageError {
  constructor(message, location) { super(message, "compile", location); }
}

export class BytecodeError extends LanguageError {
  constructor(message, location) { super(message, "bytecode", location); }
}

export class NotImplementedError extends Error {
  constructor(phase) {
    super(`${phase} is not implemented`);
    this.name = "NotImplementedError";
  }
}
