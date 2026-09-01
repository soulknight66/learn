import test from "node:test";
import assert from "node:assert/strict";

import { evaluate, parse, run } from "../starter/src/index.js";

test("the tree evaluator executes control flow and expressions", () => {
  const source = `
    let count = 0;
    while count < 3 {
      if count == 1 {
        emit true;
      } else {
        emit count;
      }
      set count = count + 1;
    }
    emit 7 / 2;
  `;

  assert.deepEqual(evaluate(parse(source)), [0, true, 2, 3.5]);
  assert.deepEqual(run(source, { backend: "tree" }), [0, true, 2, 3.5]);
});

test("variables declared in an executed block remain visible program-wide", () => {
  const source = "if true { let answer = 42; } emit answer;";
  assert.deepEqual(run(source, { backend: "tree" }), [42]);
});
