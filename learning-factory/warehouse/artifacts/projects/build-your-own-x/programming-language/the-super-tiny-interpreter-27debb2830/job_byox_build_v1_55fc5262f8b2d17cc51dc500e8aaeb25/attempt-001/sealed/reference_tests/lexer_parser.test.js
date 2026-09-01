import test from "node:test";
import assert from "node:assert/strict";
import { tokenize, parse, LexError, ParseError } from "../reference/src/index.js";

test("all token records have stable one-based locations", () => {
  const tokens = tokenize("// heading\r\nlet x=12.5;\rprint x;");
  assert.deepEqual(tokens.map((token) => [token.type, token.line, token.column]), [
    ["LET", 2, 1], ["IDENTIFIER", 2, 5], ["EQUAL", 2, 6], ["NUMBER", 2, 7],
    ["SEMICOLON", 2, 11], ["PRINT", 3, 1], ["IDENTIFIER", 3, 7],
    ["SEMICOLON", 3, 8], ["EOF", 3, 9]
  ]);
});

test("strings decode only the specified escapes", () => {
  assert.equal(tokenize('"a\\n";')[0].literal, "a\n");
  assert.equal(tokenize('"a\\t";')[0].literal, "a\t");
  assert.equal(tokenize('"a\\r";')[0].literal, "a\r");
  assert.equal(tokenize('"a\\\\b";')[0].literal, "a\\b");
  assert.equal(tokenize('"a\\\"b";')[0].literal, 'a"b');
  for (const source of ['"bad\\x";', '"raw\nline";', '"open']) {
    assert.throws(() => tokenize(source), LexError);
  }
});

test("source and token limits fail at the lexical stage", () => {
  assert.throws(() => tokenize("123", { maxSourceLength: 2 }), LexError);
  assert.throws(() => tokenize("1;", { maxTokens: 1 }), LexError);
  assert.throws(() => tokenize("", { maxTokens: 0 }), TypeError);
});

test("parser creates all control statement shapes", () => {
  const ast = parse(tokenize("let x = 0; while (x < 2) { if (x == 0) { x = 1; } else { x = 2; } }"));
  assert.equal(ast.type, "Program");
  assert.equal(ast.body[0].type, "LetStatement");
  assert.equal(ast.body[1].type, "WhileStatement");
  assert.equal(ast.body[1].body.body[0].type, "IfStatement");
  assert.deepEqual(ast.body[1].loc, { line: 1, column: 12 });
});

test("operators use the declared precedence and associativity", () => {
  const expression = parse(tokenize("result = false or true and 1 + 2 * 3 == 7;"))
    .body[0].expression;
  assert.equal(expression.type, "AssignmentExpression");
  assert.equal(expression.value.operator, "or");
  assert.equal(expression.value.right.operator, "and");
  assert.equal(expression.value.right.right.operator, "==");
  assert.equal(expression.value.right.right.left.operator, "+");
});

test("syntax errors are fail-fast and located", () => {
  assert.throws(
    () => parse(tokenize("if (true) print 1;")),
    (error) => error instanceof ParseError && error.line === 1 && error.column === 11
  );
  assert.throws(() => parse(tokenize("(1) = 2;")), ParseError);
  assert.throws(() => parse(tokenize("{{{null;}}}"), { maxParseDepth: 2 }), ParseError);
});
