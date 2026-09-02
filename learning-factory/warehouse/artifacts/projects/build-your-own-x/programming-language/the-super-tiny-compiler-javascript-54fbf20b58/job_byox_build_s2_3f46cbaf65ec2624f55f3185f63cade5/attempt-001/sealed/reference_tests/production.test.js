'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {
  CompilationLimitError,
  DEFAULT_LIMITS,
  compileWithLimits,
} = require('../production/safe-runner.js');

test('bounded compiler returns code and deterministic metrics', () => {
  const result = compileWithLimits('let x = 40; emit x + 2;');
  assert.deepEqual(Function(result.code)(), [42]);
  assert.equal(result.metrics.sourceBytes, 23);
  assert.ok(result.metrics.tokens > 0);
  assert.ok(result.metrics.astNodes > 0);
  assert.equal(result.metrics.generatedBytes, Buffer.byteLength(result.code));
  assert.equal(DEFAULT_LIMITS.maxSourceBytes, 65536);
});

test('bounded compiler rejects source before scanning when byte limit is exceeded', () => {
  assert.throws(
    () => compileWithLimits('emit "🙂";', { limits: { maxSourceBytes: 10 } }),
    (error) => error instanceof CompilationLimitError
      && error.limit === 'maxSourceBytes'
      && error.actual === 12,
  );
});

test('bounded compiler enforces token, AST, and generated-code limits', () => {
  assert.throws(
    () => compileWithLimits('emit 1;', { limits: { maxTokens: 3 } }),
    (error) => error instanceof CompilationLimitError && error.limit === 'maxTokens',
  );
  assert.throws(
    () => compileWithLimits('emit 1;', { limits: { maxAstNodes: 2 } }),
    (error) => error instanceof CompilationLimitError && error.limit === 'maxAstNodes',
  );
  assert.throws(
    () => compileWithLimits('emit 1;', { limits: { maxGeneratedBytes: 20 } }),
    (error) => error instanceof CompilationLimitError && error.limit === 'maxGeneratedBytes',
  );
});

test('bounded compiler rejects malformed limit configuration', () => {
  assert.throws(() => compileWithLimits('emit 1;', { limits: { surprise: 1 } }), /unknown limit/);
  assert.throws(() => compileWithLimits('emit 1;', { limits: { maxTokens: 0 } }), /positive integer/);
});
