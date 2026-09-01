import test from "node:test";
import assert from "node:assert/strict";

import { parse, tokenize } from "../starter/src/index.js";

test("parse builds the documented AST and honors arithmetic precedence", () => {
  const ast = parse(tokenize("emit 1 + 2 * 3;"));

  assert.equal(ast.type, "Program");
  assert.equal(ast.body.length, 1);
  assert.equal(ast.body[0].type, "EmitStatement");

  const expression = ast.body[0].expression;
  assert.equal(expression.type, "BinaryExpression");
  assert.equal(expression.operator, "+");
  assert.equal(expression.left.type, "NumberLiteral");
  assert.equal(expression.left.value, 1);
  assert.equal(expression.right.type, "BinaryExpression");
  assert.equal(expression.right.operator, "*");
  assert.deepEqual(
    [expression.right.left.value, expression.right.right.value],
    [2, 3]
  );
});

test("parse accepts source directly and represents optional else explicitly", () => {
  const ast = parse("if !false { emit (4 - 1); }");
  const branch = ast.body[0];

  assert.equal(branch.type, "IfStatement");
  assert.equal(branch.condition.type, "UnaryExpression");
  assert.equal(branch.consequent.type, "BlockStatement");
  assert.equal(branch.alternate, null);
});
