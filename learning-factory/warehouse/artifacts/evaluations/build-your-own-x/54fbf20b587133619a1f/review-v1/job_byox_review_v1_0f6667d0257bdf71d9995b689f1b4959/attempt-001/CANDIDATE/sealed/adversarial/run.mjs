import assert from "node:assert/strict";
import {
  PebbleRuntimeError,
  PebbleStepLimitError,
  PebbleSyntaxError,
  run,
} from "../reference/index.js";
import { adversarialCases } from "./cases.mjs";

const ERROR_CLASSES = Object.freeze({
  PebbleRuntimeError,
  PebbleStepLimitError,
  PebbleSyntaxError,
});

function usage() {
  return "usage: node sealed/adversarial/run.mjs [--list | --case <id>]";
}

function selectCases(arguments_) {
  if (arguments_.length === 0) return adversarialCases;
  if (arguments_.length === 1 && arguments_[0] === "--list") {
    for (const testCase of adversarialCases) console.log(testCase.id);
    return null;
  }
  if (arguments_.length === 2 && arguments_[0] === "--case") {
    const selected = adversarialCases.filter(({ id }) => id === arguments_[1]);
    if (selected.length === 0) throw new Error(`unknown case ${JSON.stringify(arguments_[1])}`);
    return selected;
  }
  throw new Error(usage());
}

function normalizedResult(result) {
  assert.ok(Array.isArray(result), "run must return an output array");
  return [...result];
}

function executeCase(testCase, backend) {
  try {
    const result = run(testCase.source, {
      backend,
      ...(testCase.maxSteps === undefined ? {} : { maxSteps: testCase.maxSteps }),
    });
    return { kind: "success", value: normalizedResult(result) };
  } catch (error) {
    return { kind: "error", error };
  }
}

function verifyExpected(testCase, backend, observation) {
  const context = `${testCase.id} (${backend})`;
  if (testCase.expectedError !== undefined) {
    assert.equal(observation.kind, "error", `${context}: expected an error`);
    const ExpectedClass = ERROR_CLASSES[testCase.expectedError.className];
    assert.equal(typeof ExpectedClass, "function", `${context}: unknown expected error class`);
    assert.ok(observation.error instanceof ExpectedClass, `${context}: wrong public error class or leaked host-language error`);
    assert.equal(observation.error.code, testCase.expectedError.code, `${context}: wrong error code`);
    assert.ok(typeof observation.error.message === "string" && observation.error.message.length > 0, `${context}: missing human-readable message`);
    return;
  }

  assert.equal(observation.kind, "success", `${context}: unexpected ${observation.error?.name ?? "error"}`);
  assert.deepEqual(observation.value, testCase.expected, `${context}: wrong observable result`);
}

function verifyParity(testCase, tree, vm) {
  const context = `${testCase.id} (backend parity)`;
  assert.equal(tree.kind, vm.kind, `${context}: completion modes differ`);
  if (tree.kind === "success") {
    assert.deepEqual(vm.value, tree.value, `${context}: results differ`);
  } else {
    assert.equal(vm.error.code, tree.error.code, `${context}: error codes differ`);
  }
}

let selected;
try {
  selected = selectCases(process.argv.slice(2));
} catch (error) {
  console.error(error.message);
  console.error(usage());
  process.exitCode = 2;
}

if (selected !== null && selected !== undefined) {
  let failures = 0;
  for (const testCase of selected) {
    const tree = executeCase(testCase, "tree");
    const vm = executeCase(testCase, "vm");
    try {
      verifyExpected(testCase, "tree", tree);
      verifyExpected(testCase, "vm", vm);
      verifyParity(testCase, tree, vm);
      console.log(`ok ${testCase.id}`);
    } catch (error) {
      failures += 1;
      console.error(`not ok ${testCase.id}`);
      console.error(error.stack ?? error);
    }
  }

  console.log(`${selected.length - failures}/${selected.length} adversarial cases passed`);
  if (failures > 0) process.exitCode = 1;
}
