#!/usr/bin/env gjs
'use strict';

// A dependency-free fallback smoke suite for generation hosts that have GJS
// but not Node. The authoritative suites use node:test.
const GLib = imports.gi.GLib;
const ByteArray = imports.byteArray;

var Buffer = { // Node-compatible subset used by the partial limit wrapper.
  byteLength(value) {
    return ByteArray.fromString(value).length;
  },
};

function read(filename) {
  const loaded = GLib.file_get_contents(filename);
  if (!loaded[0]) throw new Error(`unable to read ${filename}`);
  return ByteArray.toString(loaded[1]);
}

function loadCommonJS(filename, resolver) {
  const module = { exports: {} };
  const wrapper = Function('module', 'exports', 'require', 'Buffer', `${read(filename)}\nreturn module.exports;`);
  return wrapper(module, module.exports, resolver || ((name) => {
    throw new Error(`unexpected require: ${name}`);
  }), Buffer);
}

let assertions = 0;

function assert(condition, message) {
  assertions += 1;
  if (!condition) throw new Error(`assertion failed: ${message}`);
}

function sameValue(left, right) {
  if (Object.is(left, right)) return true;
  if (Array.isArray(left) && Array.isArray(right) && left.length === right.length) {
    return left.every((value, index) => sameValue(value, right[index]));
  }
  if (left && right && typeof left === 'object' && typeof right === 'object') {
    const leftKeys = Object.keys(left);
    const rightKeys = Object.keys(right);
    return leftKeys.length === rightKeys.length
      && leftKeys.every((key) => Object.prototype.hasOwnProperty.call(right, key)
        && sameValue(left[key], right[key]));
  }
  return false;
}

function deepEqual(actual, expected, message) {
  assert(sameValue(actual, expected), `${message}: ${JSON.stringify(actual)}`);
}

function expectCode(operation, code) {
  let caught = null;
  try {
    operation();
  } catch (error) {
    caught = error;
  }
  assert(caught !== null, `expected ${code} to be thrown`);
  assert(caught.code === code, `expected ${code}, got ${caught && caught.code}`);
}

const reference = loadCommonJS('sealed/reference/compiler.js');

const tokens = reference.tokenize('let x = 12.5; // ignored\nemit x;');
deepEqual(tokens.map((token) => [token.kind, token.value]), [
  ['KEYWORD', 'let'], ['IDENTIFIER', 'x'], ['OPERATOR', '='],
  ['NUMBER', 12.5], ['PUNCTUATION', ';'], ['KEYWORD', 'emit'],
  ['IDENTIFIER', 'x'], ['PUNCTUATION', ';'], ['EOF', null],
], 'token stream');
deepEqual(
  { line: tokens[5].line, column: tokens[5].column, offset: tokens[5].offset },
  { line: 2, column: 1, offset: 25 },
  'token location',
);

const precedence = reference.parse('emit 8 - 3 - 1 + 2 * 4;').body[0].expression;
assert(precedence.operator === '+', 'top addition');
assert(precedence.left.operator === '-', 'left associative subtraction');
assert(precedence.right.operator === '*', 'multiplication precedence');

expectCode(() => reference.tokenize('emit @;'), 'LEX_UNEXPECTED_CHARACTER');
expectCode(() => reference.tokenize('emit "\\q";'), 'LEX_UNKNOWN_ESCAPE');
expectCode(() => reference.parse('emit ;'), 'PARSE_EXPECTED_EXPRESSION');
expectCode(() => reference.analyze(reference.parse('emit absent;')), 'ANALYZE_UNKNOWN_IDENTIFIER');
expectCode(
  () => reference.analyze(reference.parse('let x = 1; let x = 2;')),
  'ANALYZE_DUPLICATE_BINDING',
);
expectCode(() => reference.analyze(reference.parse('emit pow(2);')), 'ANALYZE_WRONG_ARITY');

const source = `
  let n = 2 + 3 * 4;
  emit n;
  emit len("🙂a");
  emit n == 14 && !false;
  emit max(abs(-2), pow(2, 3));
`;
deepEqual(reference.interpret(source), [14, 2, true, 8], 'interpreter semantics');
deepEqual(Function(reference.compile(source))(), [14, 2, true, 8], 'generated semantics');
deepEqual(
  Function(reference.compile(source, { optimize: false }))(),
  [14, 2, true, 8],
  'unoptimized generated semantics',
);

const original = reference.parse('let x = (2 + 3) * 4; emit x;');
const snapshot = JSON.stringify(original);
const optimized = reference.optimize(original);
assert(JSON.stringify(original) === snapshot, 'optimizer does not mutate input');
assert(optimized !== original, 'optimizer returns a new program');
assert(optimized.body[0].initializer.value === 20, 'optimizer folds constants');

const negativeZero = reference.interpret(reference.optimize(reference.parse('emit -false;')))[0];
assert(Object.is(negativeZero, -0), 'optimizer preserves negative zero');
const nonFinite = reference.optimize(reference.parse('emit 1 / 0;'));
assert(nonFinite.body[0].expression.type === 'BinaryExpression', 'non-finite result is not a literal');

const shortCircuit = 'emit false && len(1); emit "left" || len(1);';
deepEqual(reference.interpret(shortCircuit), [false, 'left'], 'interpreter short circuit');
deepEqual(Function(reference.compile(shortCircuit))(), [false, 'left'], 'generator short circuit');

const injection = 'let constructor = "x\\n\\\"; return 99; //"; emit constructor;';
const injectionCode = reference.compile(injection);
assert(!/const constructor\b/.test(injectionCode), 'source identifier is not emitted');
deepEqual(Function(injectionCode)(), ['x\n"; return 99; //'], 'string remains data');

const bytecode = loadCommonJS(
  'sealed/alternatives/bytecode.js',
  (name) => {
    if (name === '../reference/compiler.js') return reference;
    throw new Error(`unexpected require: ${name}`);
  },
);
deepEqual(
  bytecode.runBytecode(bytecode.compileBytecode(source)),
  reference.interpret(source),
  'bytecode backend',
);
deepEqual(
  bytecode.runBytecode(bytecode.compileBytecode(shortCircuit)),
  [false, 'left'],
  'bytecode short circuit',
);

const production = loadCommonJS(
  'sealed/production/safe-runner.js',
  (name) => {
    if (name === '../reference/compiler.js') return reference;
    throw new Error(`unexpected require: ${name}`);
  },
);
const bounded = production.compileWithLimits('let x = 40; emit x + 2;');
deepEqual(Function(bounded.code)(), [42], 'bounded compiler output');
assert(bounded.metrics.sourceBytes === 23, 'bounded compiler source bytes');
expectCode(
  () => production.compileWithLimits('emit "🙂";', { limits: { maxSourceBytes: 10 } }),
  'COMPILATION_LIMIT_EXCEEDED',
);

print(`GJS_SMOKE_PASS assertions=${assertions}`);
