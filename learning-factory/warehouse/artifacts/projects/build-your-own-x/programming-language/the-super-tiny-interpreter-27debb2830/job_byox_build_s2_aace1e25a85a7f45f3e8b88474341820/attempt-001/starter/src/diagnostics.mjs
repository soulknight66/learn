export class MicaSyntaxError extends SyntaxError {
  constructor(code, message, span = null) {
    super(message);
    this.name = "MicaSyntaxError";
    this.code = code;
    this.span = span;
  }
}

export class MicaRuntimeError extends Error {
  constructor(code, message, span = null) {
    super(message);
    this.name = "MicaRuntimeError";
    this.code = code;
    this.span = span;
  }
}

export function spanFrom(start, end) {
  return {
    start: { offset: start.offset, line: start.line, column: start.column },
    end: { offset: end.offset, line: end.line, column: end.column },
  };
}
