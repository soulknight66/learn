import assert from "node:assert/strict";
import test from "node:test";

import { execute } from "../reference/src/pipeline.mjs";
import { run } from "../reference/src/vm.mjs";

test("nested block results survive scope exit without leaking names", () => {
  const source = "let kept = { let inner = 3; inner * 2; };";
  assert.throws(() => execute(source), (error) => error?.code === "E_EXPECTED_TOKEN");

  const valid = "{ let inner = 3; inner * 2; }";
  assert.deepEqual(execute(valid, { backend: "tree" }), { value: 6, output: [] });
  assert.deepEqual(execute(valid, { backend: "vm" }), { value: 6, output: [] });
  for (const backend of ["tree", "vm"]) {
    assert.throws(
      () => execute(`${valid} inner;`, { backend }),
      (error) => error?.code === "E_UNDEFINED_NAME",
    );
  }
});

test("false and nil are the only falsey values", () => {
  const cases = [
    ["false", 2],
    ["nil", 2],
    ["0", 1],
    ['""', 1],
  ];
  for (const [condition, expected] of cases) {
    const source = `if (${condition}) { 1; } else { 2; }`;
    assert.equal(execute(source, { backend: "tree" }).value, expected);
    assert.equal(execute(source, { backend: "vm" }).value, expected);
  }
});

test("a looping untrusted chunk is stopped by the instruction limit", () => {
  const chunk = {
    constants: [],
    code: [
      { op: "JUMP", arg: 0, span: null },
      { op: "HALT", arg: null, span: null },
    ],
  };
  assert.throws(() => run(chunk), (error) => error?.code === "E_INVALID_BYTECODE");
});
