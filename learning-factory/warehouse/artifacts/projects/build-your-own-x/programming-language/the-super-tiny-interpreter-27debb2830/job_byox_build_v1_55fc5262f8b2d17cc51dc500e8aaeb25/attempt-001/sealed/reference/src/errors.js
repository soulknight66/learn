export class LanguageError extends Error {
  constructor(message, stage, location = {}) {
    const line = Number.isInteger(location?.line) ? location.line : null;
    const column = Number.isInteger(location?.column) ? location.column : null;
    super(`${message}${line === null ? "" : ` at ${line}:${column}`}`);
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

export function boundedInteger(options, key, fallback) {
  const value = options?.[key] ?? fallback;
  if (!Number.isSafeInteger(value) || value < 1 || value > fallback) {
    throw new TypeError(`${key} must be an integer from 1 through ${fallback}`);
  }
  return value;
}
