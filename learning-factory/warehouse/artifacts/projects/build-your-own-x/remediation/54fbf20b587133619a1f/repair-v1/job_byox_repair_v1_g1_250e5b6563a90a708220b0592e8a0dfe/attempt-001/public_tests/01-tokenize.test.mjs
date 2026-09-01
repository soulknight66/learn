import test from "node:test";
import assert from "node:assert/strict";

import { TokenType, tokenize } from "../starter/src/index.js";

test("tokenize recognizes keywords, values, comments, and compound operators", () => {
  const tokens = tokenize("let pebble = 12.5; // skip me\nemit pebble <= 13;");

  assert.deepEqual(tokens.map(({ type }) => type), [
    TokenType.LET,
    TokenType.IDENTIFIER,
    TokenType.EQUAL,
    TokenType.NUMBER,
    TokenType.SEMICOLON,
    TokenType.EMIT,
    TokenType.IDENTIFIER,
    TokenType.LESS_EQUAL,
    TokenType.NUMBER,
    TokenType.SEMICOLON,
    TokenType.EOF
  ]);

  assert.equal(tokens[0].lexeme, "let");
  assert.equal(tokens[0].literal, null);
  assert.equal(tokens[0].line, 1);
  assert.equal(tokens[0].column, 1);
  assert.equal(tokens[3].literal, 12.5);
  assert.equal(tokens[5].line, 2);
  assert.equal(tokens.at(-1).lexeme, "");
});

test("boolean keyword tokens carry boolean literals", () => {
  const tokens = tokenize("emit true != false;");
  assert.deepEqual(
    tokens.filter(({ type }) => type === TokenType.TRUE || type === TokenType.FALSE)
      .map(({ literal }) => literal),
    [true, false]
  );
});
