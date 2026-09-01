import test from "node:test";
import assert from "node:assert/strict";
import {
  execute,
  tokenize,
  parse,
  compile,
  runBytecode,
  RuntimeError,
  BytecodeError
} from "../starter/src/index.js";

const engines = ["tree", "vm"];

for (const engine of engines) {
  test(`${engine}: scope, loops, and statement values`, () => {
    const source = `
      let n = 3;
      let text = "";
      while (n > 0) {
        text = text + "x";
        n = n - 1;
      }
      { let text = "inner"; print text; }
      print text;
      n;
    `;
    assert.deepEqual(execute(source, { engine }), {
      value: 0,
      output: ["inner", "xxx"]
    });
  });

  test(`${engine}: logical operators short-circuit and return operands`, () => {
    const source = `
      let touched = false;
      let left = "kept" or (touched = true);
      let right = null and (touched = true);
      print touched;
      left;
    `;
    assert.deepEqual(execute(source, { engine }), {
      value: "kept",
      output: ["false"]
    });
  });

  test(`${engine}: undefined variables are deterministic runtime failures`, () => {
    assert.throws(
      () => execute("print missing;", { engine }),
      (error) => error instanceof RuntimeError && error.stage === "runtime" && error.line === 1
    );
  });
}

test("compiler emits a versioned program ending in HALT", () => {
  const program = compile(parse(tokenize("print 2 + 3;")));
  assert.equal(program.version, 1);
  assert.ok(Array.isArray(program.constants));
  assert.equal(program.code.at(-1).op, "HALT");
  assert.deepEqual(runBytecode(program), { value: 5, output: ["5"] });
});

test("VM rejects malformed bytecode before producing output", () => {
  const malformed = {
    version: 1,
    constants: [],
    code: [
      { op: "PRINT", loc: { line: 1, column: 1 } },
      { op: "HALT", loc: { line: 1, column: 1 } }
    ]
  };
  assert.throws(() => runBytecode(malformed), BytecodeError);
});
