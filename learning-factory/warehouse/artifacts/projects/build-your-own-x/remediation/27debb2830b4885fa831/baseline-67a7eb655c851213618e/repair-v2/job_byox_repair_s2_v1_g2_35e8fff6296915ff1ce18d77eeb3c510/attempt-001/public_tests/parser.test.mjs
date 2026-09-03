import assert from "node:assert/strict";
import test from "node:test";

import { tokenize } from "../starter/src/lexer.mjs";
import { parse } from "../starter/src/parser.mjs";

test("parser honors multiplication precedence over addition", () => {
  const program = parse(tokenize("1 + 2 * 3;"));
  const expression = program.body[0].expression;
  assert.equal(expression.type, "BinaryExpression");
  assert.equal(expression.operator, "+");
  assert.equal(expression.left.value, 1);
  assert.equal(expression.right.operator, "*");
  assert.deepEqual(
    [expression.right.left.value, expression.right.right.value],
    [2, 3],
  );
});

test("assignment parses right-associatively", () => {
  const program = parse(tokenize("a = b = 4;"));
  const expression = program.body[0].expression;
  assert.equal(expression.type, "AssignmentExpression");
  assert.equal(expression.name, "a");
  assert.equal(expression.value.type, "AssignmentExpression");
  assert.equal(expression.value.name, "b");
});
