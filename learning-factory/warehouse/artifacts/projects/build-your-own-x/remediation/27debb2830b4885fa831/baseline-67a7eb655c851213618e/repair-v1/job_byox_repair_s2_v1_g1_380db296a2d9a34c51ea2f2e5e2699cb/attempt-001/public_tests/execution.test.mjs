import assert from "node:assert/strict";
import test from "node:test";

import { execute } from "../starter/src/pipeline.mjs";

test("tree backend evaluates bindings, assignment, output, and result", () => {
  const source = "let x = 2; x = x * 5; print x; x + 1;";
  assert.deepEqual(execute(source, { backend: "tree" }), { value: 11, output: ["10"] });
});

test("block bindings shadow without leaking", () => {
  const source = "let x = 1; { let x = 2; print x; } print x;";
  assert.deepEqual(execute(source, { backend: "tree" }), {
    value: null,
    output: ["2", "1"],
  });
});

test("tree and VM backends agree on conditional control flow", () => {
  const source = 'let n = 3; if (n >= 3) { print "large"; n * 2; } else { 0; }';
  const tree = execute(source, { backend: "tree" });
  const vm = execute(source, { backend: "vm" });
  assert.deepEqual(tree, { value: 6, output: ["large"] });
  assert.deepEqual(vm, tree);
});

test("runtime failures expose stable codes", () => {
  for (const backend of ["tree", "vm"]) {
    assert.throws(
      () => execute("missing;", { backend }),
      (error) => error?.name === "MicaRuntimeError" && error.code === "E_UNDEFINED_NAME",
    );
  }
});
