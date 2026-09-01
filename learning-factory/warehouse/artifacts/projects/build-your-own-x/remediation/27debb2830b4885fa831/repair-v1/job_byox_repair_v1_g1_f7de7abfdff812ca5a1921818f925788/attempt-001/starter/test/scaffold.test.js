import test from "node:test";
import assert from "node:assert/strict";
import * as api from "../src/index.js";

test("the required API is exported", () => {
  for (const name of ["tokenize", "parse", "interpret", "compile", "runBytecode", "execute"]) {
    assert.equal(typeof api[name], "function", `${name} must be a function`);
  }
});

test("unknown engines fail before language processing", () => {
  assert.throws(() => api.execute("", { engine: "native" }), TypeError);
});
