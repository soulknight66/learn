import assert from "node:assert/strict";
import test from "node:test";

import { MicaSyntaxError } from "../starter/src/diagnostics.mjs";
import { tokenize } from "../starter/src/lexer.mjs";

test("lexer classifies source and decodes string escapes", () => {
  const tokens = tokenize('let amount = 12.5; // ignored\nprint "row\\n" + amount;');
  assert.deepEqual(
    tokens.map((token) => token.type),
    [
      "LET", "IDENTIFIER", "EQUAL", "NUMBER", "SEMICOLON", "PRINT", "STRING", "PLUS",
      "IDENTIFIER", "SEMICOLON", "EOF",
    ],
  );
  assert.equal(tokens[3].literal, 12.5);
  assert.equal(tokens[6].literal, "row\n");
  assert.deepEqual(tokens[5].span.start, { offset: 30, line: 2, column: 1 });
});

test("lexer failures have a stable code and source span", () => {
  assert.throws(
    () => tokenize("print @;"),
    (error) => {
      assert.ok(error instanceof MicaSyntaxError);
      assert.equal(error.code, "E_UNEXPECTED_CHARACTER");
      assert.deepEqual(error.span.start, { offset: 6, line: 1, column: 7 });
      return true;
    },
  );
});
