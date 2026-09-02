'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const compiler = require('../starter/compiler.js');

test('exports the complete phase API', () => {
  for (const name of [
    'CompilerError', 'tokenize', 'parse', 'analyze', 'optimize',
    'generate', 'compile', 'interpret', 'pipeline',
  ]) {
    assert.equal(typeof compiler[name], 'function', `${name} must be a function`);
  }
});

test('scanner emits values and precise locations', () => {
  const tokens = compiler.tokenize('let x = 12.5; // skip\nemit x;');
  assert.deepEqual(
    tokens.map(({ kind, value }) => [kind, value]),
    [
      ['KEYWORD', 'let'],
      ['IDENTIFIER', 'x'],
      ['OPERATOR', '='],
      ['NUMBER', 12.5],
      ['PUNCTUATION', ';'],
      ['KEYWORD', 'emit'],
      ['IDENTIFIER', 'x'],
      ['PUNCTUATION', ';'],
      ['EOF', null],
    ],
  );
  assert.deepEqual(
    { line: tokens[3].line, column: tokens[3].column, offset: tokens[3].offset },
    { line: 1, column: 9, offset: 8 },
  );
  assert.deepEqual(
    { line: tokens[5].line, column: tokens[5].column },
    { line: 2, column: 1 },
  );
});

test('parser gives multiplication tighter precedence than addition', () => {
  const ast = compiler.parse('emit 1 + 2 * 3;');
  const expression = ast.body[0].expression;
  assert.equal(expression.type, 'BinaryExpression');
  assert.equal(expression.operator, '+');
  assert.equal(expression.left.value, 1);
  assert.equal(expression.right.operator, '*');
  assert.deepEqual(
    { line: expression.loc.line, column: expression.loc.column, offset: expression.loc.offset },
    { line: 1, column: 6, offset: 5 },
  );
});

test('analysis rejects unknown and duplicate bindings with structured errors', () => {
  assert.throws(
    () => compiler.analyze(compiler.parse('emit absent;')),
    (error) => error instanceof compiler.CompilerError
      && error.phase === 'analyze'
      && error.code === 'ANALYZE_UNKNOWN_IDENTIFIER'
      && error.line === 1
      && error.column === 6,
  );
  assert.throws(
    () => compiler.interpret('let x = 1; let x = 2; emit x;'),
    (error) => error instanceof compiler.CompilerError
      && error.code === 'ANALYZE_DUPLICATE_BINDING',
  );
});

test('interpreter implements expressions, built-ins, and Unicode len', () => {
  const output = compiler.interpret(`
    let n = 2 + 3 * 4;
    emit n;
    emit "ok";
    emit n == 14 && !false;
    emit len("🙂a");
  `);
  assert.deepEqual(output, [14, 'ok', true, 2]);
});

test('optimizer is non-mutating and preserves observable behavior', () => {
  const ast = compiler.parse('let x = (2 + 3) * 4; emit x == 20;');
  const before = JSON.stringify(ast);
  compiler.analyze(ast);
  const optimized = compiler.optimize(ast);
  assert.equal(JSON.stringify(ast), before);
  assert.notStrictEqual(optimized, ast);
  assert.deepEqual(compiler.interpret(ast), compiler.interpret(optimized));
  assert.equal(optimized.body[0].initializer.type, 'Literal');
  assert.equal(optimized.body[0].initializer.value, 20);
});

test('generated code uses safe bindings and matches the interpreter', () => {
  const source = 'let constructor = 2; emit constructor + pow(2, 3);';
  const code = compiler.compile(source);
  assert.match(code, /^"use strict";/);
  assert.doesNotMatch(code, /const constructor\b/);
  const compiledOutput = Function(code)(); // The harness executes compiler output; the interpreter must not.
  assert.deepEqual(compiledOutput, compiler.interpret(source));
  assert.deepEqual(compiledOutput, [10]);
});

test('lex and parse failures use stable codes', () => {
  assert.throws(
    () => compiler.tokenize('emit @;'),
    (error) => error instanceof compiler.CompilerError
      && error.code === 'LEX_UNEXPECTED_CHARACTER'
      && error.column === 6,
  );
  assert.throws(
    () => compiler.parse('emit ;'),
    (error) => error instanceof compiler.CompilerError
      && error.code === 'PARSE_EXPECTED_EXPRESSION',
  );
});

test('pipeline exposes deterministic phase artifacts', () => {
  const result = compiler.pipeline('emit 6 * 7;', { optimize: false });
  assert.equal(result.tokens.at(-1).kind, 'EOF');
  assert.equal(result.ast.type, 'Program');
  assert.strictEqual(result.optimizedAst, result.ast);
  assert.equal(result.analysis.ast, result.ast);
  assert.equal(typeof result.code, 'string');
});
