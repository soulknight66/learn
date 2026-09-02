'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const reference = require('../reference/compiler.js');

function runGenerated(source, options) {
  return Function(reference.compile(source, options))();
}

test('tokenizes every terminal class and appends EOF', () => {
  const tokens = reference.tokenize('let _x2 = 10.25; emit !false || _x2 >= 2 && "a\\n" != "b";');
  assert.deepEqual(
    tokens.map((token) => token.kind),
    [
      'KEYWORD', 'IDENTIFIER', 'OPERATOR', 'NUMBER', 'PUNCTUATION',
      'KEYWORD', 'OPERATOR', 'KEYWORD', 'OPERATOR', 'IDENTIFIER',
      'OPERATOR', 'NUMBER', 'OPERATOR', 'STRING', 'OPERATOR', 'STRING',
      'PUNCTUATION', 'EOF',
    ],
  );
  assert.equal(tokens[13].value, 'a\n');
  assert.equal(tokens.at(-1).value, null);
});

test('tracks locations through comments and CRLF', () => {
  const tokens = reference.tokenize('// first\r\nemit 7;');
  assert.deepEqual(
    { line: tokens[0].line, column: tokens[0].column, offset: tokens[0].offset },
    { line: 2, column: 1, offset: 10 },
  );
  assert.deepEqual(
    { line: tokens[1].line, column: tokens[1].column, offset: tokens[1].offset },
    { line: 2, column: 6, offset: 15 },
  );
});

test('scanner errors are structured and do not stall', () => {
  const cases = [
    ['emit @;', 'LEX_UNEXPECTED_CHARACTER'],
    ['emit "open;', 'LEX_UNTERMINATED_STRING'],
    ['emit "line\nbreak";', 'LEX_UNTERMINATED_STRING'],
    ['emit "\\q";', 'LEX_UNKNOWN_ESCAPE'],
    ['emit 1.;', 'LEX_UNEXPECTED_CHARACTER'],
  ];
  for (const [source, code] of cases) {
    assert.throws(
      () => reference.tokenize(source),
      (error) => error instanceof reference.CompilerError
        && error.phase === 'lex'
        && error.code === code,
    );
  }
});

test('parses left associativity and grouping', () => {
  const [first, second] = reference.parse('emit 8 - 3 - 1; emit 8 - (3 - 1);').body;
  assert.equal(first.expression.left.operator, '-');
  assert.equal(first.expression.right.value, 1);
  assert.equal(second.expression.right.operator, '-');
  assert.deepEqual(reference.interpret('emit 8 - 3 - 1; emit 8 - (3 - 1);'), [4, 6]);
});

test('parses all precedence levels in the specified order', () => {
  const expression = reference.parse('emit 1 + 2 * 3 < 8 == true && false || true;').body[0].expression;
  assert.equal(expression.operator, '||');
  assert.equal(expression.left.operator, '&&');
  assert.equal(expression.left.left.operator, '==');
  assert.equal(expression.left.left.left.operator, '<');
  assert.equal(expression.left.left.left.left.operator, '+');
  assert.equal(expression.left.left.left.left.right.operator, '*');
});

test('parser reports incomplete statements and expressions', () => {
  const cases = [
    ['let = 1;', 'PARSE_EXPECTED_IDENTIFIER'],
    ['let x 1;', 'PARSE_EXPECTED_ASSIGN'],
    ['let x = 1', 'PARSE_EXPECTED_SEMICOLON'],
    ['emit ;', 'PARSE_EXPECTED_EXPRESSION'],
    ['emit pow(1,);', 'PARSE_EXPECTED_EXPRESSION'],
    ['emit (1 + 2;', 'PARSE_EXPECTED_RPAREN'],
    ['1 + 2;', 'PARSE_EXPECTED_STATEMENT'],
  ];
  for (const [source, code] of cases) {
    assert.throws(
      () => reference.parse(source),
      (error) => error instanceof reference.CompilerError
        && error.phase === 'parse'
        && error.code === code,
      source,
    );
  }
});

test('AST nodes carry start locations', () => {
  const ast = reference.parse('\nemit -(2 + 3);');
  assert.deepEqual(ast.loc, { line: 2, column: 1, offset: 1 });
  assert.deepEqual(ast.body[0].loc, { line: 2, column: 1, offset: 1 });
  assert.deepEqual(ast.body[0].expression.loc, { line: 2, column: 6, offset: 6 });
  assert.deepEqual(ast.body[0].expression.argument.loc, { line: 2, column: 8, offset: 8 });
});

test('analysis resolves sequential bindings and assigns opaque IDs', () => {
  const ast = reference.parse('let constructor = 2; let y = constructor + 1; emit y;');
  const result = reference.analyze(ast);
  assert.deepEqual(
    result.symbols,
    [
      { id: 0, sourceName: 'constructor', generatedName: 'v_0' },
      { id: 1, sourceName: 'y', generatedName: 'v_1' },
    ],
  );
  assert.equal(result.declarationIds.get(ast.body[0]), 0);
  assert.equal(result.referenceIds.get(ast.body[1].initializer.left), 0);
});

test('analysis rejects invalid names, calls, and arities', () => {
  const cases = [
    ['let x = x;', 'ANALYZE_UNKNOWN_IDENTIFIER'],
    ['let x = 1; let x = 2;', 'ANALYZE_DUPLICATE_BINDING'],
    ['let abs = 1;', 'ANALYZE_BUILTIN_BINDING'],
    ['emit mystery(1);', 'ANALYZE_UNKNOWN_FUNCTION'],
    ['let x = 1; emit x();', 'ANALYZE_NON_CALLABLE'],
    ['emit pow(2);', 'ANALYZE_WRONG_ARITY'],
    ['emit min();', 'ANALYZE_WRONG_ARITY'],
    ['emit (abs(1))(2);', 'ANALYZE_INVALID_CALL_TARGET'],
  ];
  for (const [source, code] of cases) {
    assert.throws(
      () => reference.analyze(reference.parse(source)),
      (error) => error instanceof reference.CompilerError
        && error.phase === 'analyze'
        && error.code === code,
      source,
    );
  }
});

test('interpreter implements built-ins and primitive operators', () => {
  const source = `
    emit abs(-3);
    emit sqrt(81);
    emit pow(2, 5);
    emit min(9, 4, 7);
    emit max(9, 4, 7);
    emit len("🙂a");
    emit "rip" + "ple";
    emit 3 != "3";
  `;
  assert.deepEqual(reference.interpret(source), [3, 9, 32, 4, 9, 2, 'ripple', true]);
});

test('logical operators short-circuit and return operand values', () => {
  const source = 'emit false && len(7); emit true || len(7); emit "left" || "right";';
  assert.deepEqual(reference.interpret(source), [false, true, 'left']);
  assert.deepEqual(runGenerated(source), [false, true, 'left']);
});

test('len rejects non-string values only when evaluated', () => {
  assert.throws(() => reference.interpret('emit len(10);'), {
    name: 'TypeError',
    message: 'len expects a string',
  });
  assert.throws(() => runGenerated('emit len(10);'), {
    name: 'TypeError',
    message: 'len expects a string',
  });
});

test('optimizer deeply clones and folds finite constants', () => {
  const ast = reference.parse('let x = -(2 + 3) * 4; emit x == -20;');
  const snapshot = JSON.stringify(ast);
  const optimized = reference.optimize(ast);
  assert.equal(JSON.stringify(ast), snapshot);
  assert.notStrictEqual(optimized, ast);
  assert.notStrictEqual(optimized.body[0], ast.body[0]);
  assert.notStrictEqual(optimized.body[0].name, ast.body[0].name);
  assert.deepEqual(optimized.body[0].initializer.value, -20);
  assert.deepEqual(reference.interpret(optimized), [true]);
});

test('optimizer leaves non-finite results for runtime evaluation', () => {
  const optimized = reference.optimize(reference.parse('emit 1 / 0; emit 0 / 0;'));
  assert.equal(optimized.body[0].expression.type, 'BinaryExpression');
  assert.equal(optimized.body[1].expression.type, 'BinaryExpression');
  const result = reference.interpret(optimized);
  assert.equal(result[0], Infinity);
  assert.ok(Number.isNaN(result[1]));
});

test('optimizer and generator preserve negative zero', () => {
  const optimized = reference.optimize(reference.parse('emit -false;'));
  assert.ok(Object.is(optimized.body[0].expression.value, -0));
  assert.ok(Object.is(reference.interpret(optimized)[0], -0));
  assert.ok(Object.is(runGenerated('emit -false;')[0], -0));
});

test('generator escapes strings and never declares a source spelling', () => {
  const source = 'let constructor = "x\\n\\\"; return 99; //"; emit constructor;';
  const code = reference.compile(source);
  assert.doesNotMatch(code, /const constructor\b/);
  assert.doesNotMatch(code, /^\s*return 99; \/\//m);
  assert.deepEqual(Function(code)(), ['x\n"; return 99; //']);
});

test('generated equality is strict and output order is stable', () => {
  const source = 'emit 3 == "3"; emit 3 != "3"; emit 1 + 2;';
  const code = reference.compile(source, { optimize: false });
  assert.match(code, /===/);
  assert.match(code, /!==/);
  assert.deepEqual(Function(code)(), [false, true, 3]);
});

test('optimized and unoptimized compilation agree with interpretation', () => {
  const programs = [
    'emit 1 + 2 * 3;',
    'let x = 8; emit (x - 3) * 2;',
    'emit max(1, pow(2, 3), abs(-4));',
    'emit "a" + "b" == "ab";',
    'emit !(2 > 3) && 4 <= 4;',
    'let a = 2; let b = a * a + 1; emit b % 3;',
    'emit sqrt(-1);',
    'emit 1 / 0;',
  ];
  for (const source of programs) {
    const expected = reference.interpret(source);
    assert.deepEqual(runGenerated(source), expected, `optimized: ${source}`);
    assert.deepEqual(runGenerated(source, { optimize: false }), expected, `plain: ${source}`);
  }
});

test('pipeline exposes coherent artifacts', () => {
  const optimized = reference.pipeline('emit 40 + 2;');
  assert.equal(optimized.tokens.at(-1).kind, 'EOF');
  assert.notStrictEqual(optimized.optimizedAst, optimized.ast);
  assert.strictEqual(optimized.analysis.ast, optimized.optimizedAst);
  assert.deepEqual(Function(optimized.code)(), [42]);

  const plain = reference.pipeline('emit 40 + 2;', { optimize: false });
  assert.strictEqual(plain.optimizedAst, plain.ast);
  assert.strictEqual(plain.analysis.ast, plain.ast);
});

test('interpreter implementation does not evaluate generated code', () => {
  const implementation = fs.readFileSync(require.resolve('../reference/compiler.js'), 'utf8');
  const interpretStart = implementation.indexOf('function interpret(');
  const pipelineStart = implementation.indexOf('function pipeline(', interpretStart);
  const interpretSource = implementation.slice(interpretStart, pipelineStart);
  assert.doesNotMatch(interpretSource, /\beval\s*\(/);
  assert.doesNotMatch(interpretSource, /\bFunction\s*\(/);
  assert.doesNotMatch(interpretSource, /generate\s*\(/);
});
