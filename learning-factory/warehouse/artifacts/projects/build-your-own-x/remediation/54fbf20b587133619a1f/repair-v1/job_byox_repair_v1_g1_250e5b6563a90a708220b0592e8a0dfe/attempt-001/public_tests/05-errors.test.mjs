import test from "node:test";
import assert from "node:assert/strict";

import {
  PebbleSyntaxError,
  PebbleRuntimeError,
  PebbleStepLimitError,
  execute,
  parse,
  run
} from "../starter/src/index.js";

function assertRuntimeCode(source, code) {
  assert.throws(
    () => run(source, { backend: "tree" }),
    (error) => error instanceof PebbleRuntimeError && error.code === code
  );
}

test("duplicate definitions and undefined names are runtime errors", () => {
  assertRuntimeCode("let stone = 1; let stone = 2;", "DUPLICATE_VARIABLE");
  assertRuntimeCode("emit missing;", "UNDEFINED_VARIABLE");
  assertRuntimeCode("set missing = 1;", "UNDEFINED_VARIABLE");
});

test("invalid operand types and division by zero have stable categories", () => {
  assertRuntimeCode("emit true + 1;", "TYPE_ERROR");
  assertRuntimeCode("if 1 { emit 0; }", "TYPE_ERROR");
  assertRuntimeCode("emit 9 / 0;", "DIVISION_BY_ZERO");
});

test("arithmetic cannot create non-finite Pebble numbers", () => {
  const hugeFiniteLiteral = `1${"0".repeat(308)}`;
  for (const backend of ["tree", "vm"]) {
    assert.throws(
      () => run(`emit ${hugeFiniteLiteral} * 10;`, { backend }),
      (error) => error instanceof PebbleRuntimeError && error.code === "NON_FINITE_NUMBER"
    );
  }
});

test("maxSteps stops a non-terminating program on both backends", () => {
  for (const backend of ["tree", "vm"]) {
    assert.throws(
      () => run("while true {}", { backend, maxSteps: 20 }),
      (error) => error instanceof PebbleStepLimitError
        && error.code === "STEP_LIMIT_EXCEEDED"
    );
  }
});

test("maxSteps uses the documented backend-specific exact boundary", () => {
  assert.deepEqual(run("emit 1;", { backend: "tree", maxSteps: 2 }), [1]);
  assert.throws(
    () => run("emit 1;", { backend: "vm", maxSteps: 2 }),
    (error) => error instanceof PebbleStepLimitError
      && error.code === "STEP_LIMIT_EXCEEDED"
  );
  assert.deepEqual(run("emit 1;", { backend: "vm", maxSteps: 3 }), [1]);
});

test("invalid backend and step options are Pebble runtime errors", () => {
  assert.throws(
    () => run("", { backend: "native" }),
    (error) => error instanceof PebbleRuntimeError && error.code === "INVALID_OPTIONS"
  );
  assert.throws(
    () => run("", { maxSteps: 0 }),
    (error) => error instanceof PebbleRuntimeError && error.code === "INVALID_OPTIONS"
  );
  assert.throws(
    () => run("", { maxSteps: null }),
    (error) => error instanceof PebbleRuntimeError && error.code === "INVALID_OPTIONS"
  );
  assert.throws(
    () => run("", { extra: true }),
    (error) => error instanceof PebbleRuntimeError && error.code === "INVALID_OPTIONS"
  );
});

test("malformed source reports Pebble syntax errors", () => {
  assert.throws(() => parse("emit 1"), PebbleSyntaxError);
  assert.throws(
    () => parse("emit 1;\n@"),
    (error) => error instanceof PebbleSyntaxError
      && error.line === 2
      && error.column === 1
  );
});

test("the VM rejects invalid bytecode before executing it", () => {
  const bytecode = {
    format: "pebble-bytecode",
    version: 1,
    constants: [],
    instructions: [{ op: "UNKNOWN" }, { op: "HALT" }]
  };

  assert.throws(
    () => execute(bytecode),
    (error) => error instanceof PebbleRuntimeError && error.code === "INVALID_BYTECODE"
  );
});
