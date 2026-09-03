import assert from "node:assert/strict";
import test from "node:test";

import { MicaRuntimeError } from "../reference/src/diagnostics.mjs";
import { execute } from "../reference/src/pipeline.mjs";
import { run } from "../reference/src/vm.mjs";

function rejectsInvalidBytecode(callback) {
  assert.throws(
    callback,
    (error) => error instanceof MicaRuntimeError && error.code === "E_INVALID_BYTECODE",
  );
}

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
  rejectsInvalidBytecode(() => run(chunk));
});

test("invalid opcode types are rejected without host coercion", () => {
  let coercionCalls = 0;
  const hostileOpcode = {
    toString() {
      coercionCalls += 1;
      throw new Error("opcode coercion must not execute");
    },
  };
  for (const op of [Symbol("bad"), hostileOpcode]) {
    rejectsInvalidBytecode(() => run({
      constants: [],
      code: [{ op, arg: null, span: null }],
    }));
  }
  assert.equal(coercionCalls, 0);
});

test("malformed source spans are rejected before execution", () => {
  const position = (offset, line, column) => ({ offset, line, column });
  const malformedSpans = [
    "not-a-span",
    {},
    { start: position(0, 1, 1), end: null },
    { start: position(-1, 1, 1), end: position(0, 1, 1) },
    { start: position(0, 0, 1), end: position(0, 1, 1) },
    { start: position(0, 1, 0), end: position(0, 1, 1) },
    { start: position(0.5, 1, 1), end: position(1, 1, 2) },
    { start: position(2, 1, 3), end: position(1, 1, 2) },
    { start: position(0, 2, 1), end: position(1, 1, 2) },
    { start: position(0, 1, 3), end: position(1, 1, 2) },
  ];
  for (const span of malformedSpans) {
    let caught;
    try {
      run({
        constants: [],
        code: [
          { op: "LOAD", arg: "missing", span },
          { op: "HALT", arg: null, span: null },
        ],
      });
    } catch (error) {
      caught = error;
    }
    assert.ok(caught instanceof MicaRuntimeError);
    assert.equal(caught.code, "E_INVALID_BYTECODE");
    assert.equal(caught.span, null, "unvalidated span data must not escape on the error");
  }
});

test("bytecode validation does not invoke accessors for required fields", () => {
  let getterCalls = 0;
  const instruction = { arg: null, span: null };
  Object.defineProperty(instruction, "op", {
    enumerable: true,
    get() {
      getterCalls += 1;
      return "HALT";
    },
  });
  rejectsInvalidBytecode(() => run({ constants: [], code: [instruction] }));
  assert.equal(getterCalls, 0);
});
