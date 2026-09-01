import test from "node:test";
import assert from "node:assert/strict";

import { compile, execute, parse, run } from "../starter/src/index.js";

const source = `
  let product = 1;
  let factor = 4;
  while factor > 1 {
    set product = product * factor;
    set factor = factor - 1;
  }
  emit product;
`;

test("compile returns a versioned bytecode envelope executable by the VM", () => {
  const ast = parse(source);
  const bytecode = compile(ast);

  assert.equal(bytecode.format, "pebble-bytecode");
  assert.equal(bytecode.version, 1);
  assert.ok(Array.isArray(bytecode.constants));
  assert.ok(Array.isArray(bytecode.instructions));
  assert.deepEqual(compile(ast), bytecode, "compilation is deterministic");

  const beforeExecution = structuredClone(bytecode);
  assert.deepEqual(execute(bytecode), [24]);
  assert.deepEqual(bytecode, beforeExecution, "execution does not mutate bytecode");
});

test("tree and VM backends have matching observable output", () => {
  assert.deepEqual(run(source, { backend: "vm" }), run(source, { backend: "tree" }));
  assert.deepEqual(run(source), [24], "run defaults to the VM backend");
});
