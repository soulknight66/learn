'use strict';

const { pipeline } = require('../reference/compiler.js');

class CompilationLimitError extends Error {
  constructor(limit, maximum, actual) {
    super(`${limit} limit exceeded: maximum ${maximum}, observed ${actual}`);
    this.name = 'CompilationLimitError';
    this.code = 'COMPILATION_LIMIT_EXCEEDED';
    this.limit = limit;
    this.maximum = maximum;
    this.actual = actual;
  }
}

const DEFAULT_LIMITS = Object.freeze({
  maxSourceBytes: 64 * 1024,
  maxTokens: 20000,
  maxAstNodes: 40000,
  maxGeneratedBytes: 256 * 1024,
});

function checkedLimits(overrides) {
  if (overrides === undefined) {
    return { ...DEFAULT_LIMITS };
  }
  if (!overrides || typeof overrides !== 'object' || Array.isArray(overrides)) {
    throw new TypeError('limits must be an object');
  }
  const limits = { ...DEFAULT_LIMITS };
  for (const key of Object.keys(overrides)) {
    if (!Object.prototype.hasOwnProperty.call(DEFAULT_LIMITS, key)) {
      throw new TypeError(`unknown limit: ${key}`);
    }
    const value = overrides[key];
    if (!Number.isInteger(value) || value < 1) {
      throw new RangeError(`${key} must be a positive integer`);
    }
    limits[key] = value;
  }
  return limits;
}

function enforce(name, maximum, actual) {
  if (actual > maximum) {
    throw new CompilationLimitError(name, maximum, actual);
  }
}

function countAstNodes(ast, maximum) {
  const pending = [ast];
  const seen = new WeakSet();
  let count = 0;
  while (pending.length > 0) {
    const value = pending.pop();
    if (!value || typeof value !== 'object' || seen.has(value)) {
      continue;
    }
    seen.add(value);
    count += 1;
    enforce('maxAstNodes', maximum, count);
    for (const [key, child] of Object.entries(value)) {
      if (key === 'loc') {
        continue;
      }
      if (Array.isArray(child)) {
        for (const item of child) {
          pending.push(item);
        }
      } else if (child && typeof child === 'object') {
        pending.push(child);
      }
    }
  }
  return count;
}

/**
 * Compile under deterministic size ceilings. This does not execute code and is
 * not a process sandbox; see PRODUCTIONIZATION.md before any service use.
 */
function compileWithLimits(source, options = {}) {
  if (typeof source !== 'string') {
    throw new TypeError('source must be a string');
  }
  if (!options || typeof options !== 'object' || Array.isArray(options)) {
    throw new TypeError('options must be an object');
  }
  const limitOverrides = Object.prototype.hasOwnProperty.call(options, 'limits')
    ? options.limits
    : undefined;
  const shouldOptimize = !Object.prototype.hasOwnProperty.call(options, 'optimize')
    || options.optimize !== false;
  const limits = checkedLimits(limitOverrides);
  enforce('maxSourceBytes', limits.maxSourceBytes, Buffer.byteLength(source, 'utf8'));

  const result = pipeline(source, { optimize: shouldOptimize });
  enforce('maxTokens', limits.maxTokens, result.tokens.length);
  countAstNodes(result.ast, limits.maxAstNodes);
  if (result.optimizedAst !== result.ast) {
    countAstNodes(result.optimizedAst, limits.maxAstNodes);
  }
  enforce('maxGeneratedBytes', limits.maxGeneratedBytes, Buffer.byteLength(result.code, 'utf8'));
  return {
    code: result.code,
    metrics: {
      sourceBytes: Buffer.byteLength(source, 'utf8'),
      tokens: result.tokens.length,
      astNodes: countAstNodes(result.ast, limits.maxAstNodes),
      generatedBytes: Buffer.byteLength(result.code, 'utf8'),
    },
  };
}

module.exports = {
  CompilationLimitError,
  DEFAULT_LIMITS,
  compileWithLimits,
};
