import test from "node:test";
import assert from "node:assert/strict";
import { toPostfix } from "./buggy-parser.js";

test("multiplication binds more tightly than addition", () => {
  assert.deepEqual(toPostfix([1, "+", 2, "*", 3]), [1, 2, 3, "*", "+"]);
});

test("operators of equal precedence associate to the left", () => {
  assert.deepEqual(toPostfix([8, "-", 3, "+", 1]), [8, 3, "-", 1, "+"]);
});
