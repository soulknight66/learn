import test from "node:test";
import assert from "node:assert/strict";
import { tokenize, parse, LexError, ParseError } from "../starter/src/index.js";

test("lexer decodes literals and tracks token starts", () => {
  const tokens = tokenize("let greeting = \"hi\\nthere\";\nprint greeting;");
  assert.deepEqual(
    tokens.map(({ type, literal, line, column }) => ({ type, literal, line, column })),
    [
      { type: "LET", literal: null, line: 1, column: 1 },
      { type: "IDENTIFIER", literal: null, line: 1, column: 5 },
      { type: "EQUAL", literal: null, line: 1, column: 14 },
      { type: "STRING", literal: "hi\nthere", line: 1, column: 16 },
      { type: "SEMICOLON", literal: null, line: 1, column: 27 },
      { type: "PRINT", literal: null, line: 2, column: 1 },
      { type: "IDENTIFIER", literal: null, line: 2, column: 7 },
      { type: "SEMICOLON", literal: null, line: 2, column: 15 },
      { type: "EOF", literal: null, line: 2, column: 16 }
    ]
  );
});

test("lexer rejects an unsupported escape with a typed location", () => {
  assert.throws(
    () => tokenize('print "bad\\q";'),
    (error) => error instanceof LexError && error.stage === "lex" && error.line === 1
  );
});

test("parser represents precedence and right-associative assignment", () => {
  const ast = parse(tokenize("a = b = 1 + 2 * 3;"));
  const outer = ast.body[0].expression;
  assert.equal(outer.type, "AssignmentExpression");
  assert.equal(outer.name.name, "a");
  assert.equal(outer.value.name.name, "b");
  assert.equal(outer.value.value.operator, "+");
  assert.equal(outer.value.value.right.operator, "*");
});

test("parser rejects a non-identifier assignment target", () => {
  assert.throws(() => parse(tokenize("(1 + 2) = 3;")), ParseError);
});
