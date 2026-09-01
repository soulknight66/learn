import test from "node:test";
import assert from "node:assert/strict";
import { execute, RuntimeError } from "../reference/src/index.js";

function both(source, expected) {
  const tree = execute(source, { engine: "tree" });
  const vm = execute(source, { engine: "vm" });
  assert.deepEqual(tree, expected);
  assert.deepEqual(vm, expected);
}

test("empty and ordinary programs agree", () => {
  both("", { value: null, output: [] });
  both("print 1 + 2 * 3;", { value: 7, output: ["7"] });
  both('print "a" + "b"; null;', { value: null, output: ["ab"] });
});

test("loop result and outer assignment agree", () => {
  both(`
    let product = 1;
    let n = 5;
    while (n > 1) {
      product = product * n;
      n = n - 1;
    }
    print product;
  `, { value: 120, output: ["120"] });
});

test("blocks shadow and assignments find the nearest binding", () => {
  both(`
    let x = "outer";
    { let x = "inner"; x = x + "!"; print x; }
    print x;
  `, { value: "outer", output: ["inner!", "outer"] });
});

test("prototype-like binding names work in both engines", () => {
  both(`
    let constructor = 1;
    let toString = 2;
    let hasOwnProperty = 3;
    let __proto__ = 4;
    constructor + toString + hasOwnProperty + __proto__;
  `, { value: 10, output: [] });
});

test("flat left-associative expressions work around the former recursion boundary", () => {
  for (const terms of [999, 1000, 1001]) {
    const source = `${Array.from({ length: terms }, () => "1").join("+")};`;
    both(source, { value: terms, output: [] });
  }
});

test("flat logical chains remain short-circuiting without recursive tree walks", () => {
  const source = `${Array.from({ length: 1200 }, () => "true").join(" or ")} or missing;`;
  both(source, { value: true, output: [] });
});

test("grouped identifiers can be assigned in both engines", () => {
  both("let value = 1; ((value)) = 2; value;", { value: 2, output: [] });
});

test("false and null are the only falsey values", () => {
  both(`
    print 0 or 9;
    print "" and "right";
    print null or "fallback";
    print false and missing;
  `, { value: false, output: ["0", "right", "fallback", "false"] });
});

test("runtime error families agree by class and location", () => {
  for (const source of [
    "missing;", "let x = 1; let x = 2;", "1 + true;", "9 / 0;", "missing = 1;"
  ]) {
    for (const engine of ["tree", "vm"]) {
      assert.throws(
        () => execute(source, { engine }),
        (error) => error instanceof RuntimeError && error.stage === "runtime" && error.line === 1
      );
    }
  }
});

test("nonterminating programs encounter each engine's deterministic step limit", () => {
  const source = "while (true) { null; }";
  for (const engine of ["tree", "vm"]) {
    assert.throws(
      () => execute(source, { engine, maxSteps: 30 }),
      (error) => error instanceof RuntimeError && /step limit 30/.test(error.message)
    );
  }
});

test("equal numeric step budgets remain engine-local", () => {
  assert.deepEqual(execute("print 1;", { engine: "tree", maxSteps: 2 }), {
    value: 1,
    output: ["1"]
  });
  assert.throws(
    () => execute("print 1;", { engine: "vm", maxSteps: 2 }),
    (error) => error instanceof RuntimeError && /step limit 2/.test(error.message)
  );
});
