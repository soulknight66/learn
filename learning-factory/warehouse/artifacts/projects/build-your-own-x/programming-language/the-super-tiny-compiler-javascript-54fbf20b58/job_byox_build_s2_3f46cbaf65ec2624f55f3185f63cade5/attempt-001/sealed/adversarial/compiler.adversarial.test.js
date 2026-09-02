'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const reference = require('../reference/compiler.js');
const { compileWithLimits, CompilationLimitError } = require('../production/safe-runner.js');

test('all single ASCII bytes either tokenize or fail structurally', { timeout: 2000 }, () => {
  for (let codePoint = 0; codePoint < 128; codePoint += 1) {
    const character = String.fromCharCode(codePoint);
    try {
      const tokens = reference.tokenize(character);
      assert.equal(tokens.at(-1).kind, 'EOF');
    } catch (error) {
      assert.ok(error instanceof reference.CompilerError, `byte ${codePoint}`);
      assert.equal(error.phase, 'lex');
      assert.ok(Number.isInteger(error.offset));
    }
  }
});

test('long flat operator chains parse without expression-parser recursion', { timeout: 2000 }, () => {
  const source = `emit ${Array(1500).fill('1').join(' + ')};`;
  const ast = reference.parse(source);
  assert.equal(ast.body.length, 1);
  assert.equal(ast.body[0].expression.type, 'BinaryExpression');
});

test('prototype-like identifiers remain ordinary bindings', () => {
  const source = `
    let constructor = 1;
    let toString = constructor + 1;
    let __proto__ = toString + 1;
    emit __proto__;
  `;
  assert.deepEqual(reference.interpret(source), [3]);
  assert.deepEqual(Function(reference.compile(source))(), [3]);
});

test('string payload cannot escape the generated literal', () => {
  const payloads = [
    '"; throw new Error("escaped"); //',
    '\\"\\\\\\n\\t',
    '\u2028return 91;\u2029',
    '${globalThis.process}',
  ];
  for (const payload of payloads) {
    const sourceLiteral = JSON.stringify(payload);
    const source = `emit ${sourceLiteral};`;
    assert.deepEqual(Function(reference.compile(source))(), [payload]);
  }
});

test('skipped logical branches cannot trigger len type errors', () => {
  const source = 'emit 0 && len(0); emit 1 || len(0);';
  assert.deepEqual(reference.interpret(source), [0, 1]);
  assert.deepEqual(Function(reference.compile(source))(), [0, 1]);
});

test('source byte limit counts UTF-8 rather than UTF-16 units', () => {
  assert.throws(
    () => compileWithLimits('emit "🙂🙂";', { limits: { maxSourceBytes: 15 } }),
    (error) => error instanceof CompilationLimitError
      && error.limit === 'maxSourceBytes'
      && error.actual === 16,
  );
});

test('repeated invalid characters always report the first offset', { timeout: 1000 }, () => {
  const source = `${' '.repeat(4096)}@@@@@@@@`;
  assert.throws(
    () => reference.tokenize(source),
    (error) => error.code === 'LEX_UNEXPECTED_CHARACTER'
      && error.offset === 4096
      && error.column === 4097,
  );
});
