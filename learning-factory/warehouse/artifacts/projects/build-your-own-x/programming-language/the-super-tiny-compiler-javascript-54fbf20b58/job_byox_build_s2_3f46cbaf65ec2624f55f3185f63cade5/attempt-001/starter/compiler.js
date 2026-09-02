'use strict';

/** A source-facing failure with stable machine-readable fields. */
class CompilerError extends Error {
  constructor(phase, code, message, loc) {
    const where = loc || { line: 1, column: 1, offset: 0 };
    super(`${code} at ${where.line}:${where.column}: ${message}`);
    this.name = 'CompilerError';
    this.phase = phase;
    this.code = code;
    this.line = where.line;
    this.column = where.column;
    this.offset = where.offset;
  }
}

function unfinished(phase) {
  throw new Error(`TODO: implement Ripple ${phase}`);
}

function tokenize(_source) {
  return unfinished('scanner');
}

function parse(_sourceOrTokens) {
  return unfinished('parser');
}

function analyze(_ast) {
  return unfinished('semantic analyzer');
}

function optimize(_ast) {
  return unfinished('optimizer');
}

function generate(_ast, _analysis) {
  return unfinished('JavaScript generator');
}

function compile(_source, _options) {
  return unfinished('compiler pipeline');
}

function interpret(_sourceOrAst) {
  return unfinished('tree-walking interpreter');
}

function pipeline(_source, _options) {
  return unfinished('compiler pipeline');
}

module.exports = {
  CompilerError,
  tokenize,
  parse,
  analyze,
  optimize,
  generate,
  compile,
  interpret,
  pipeline,
};
