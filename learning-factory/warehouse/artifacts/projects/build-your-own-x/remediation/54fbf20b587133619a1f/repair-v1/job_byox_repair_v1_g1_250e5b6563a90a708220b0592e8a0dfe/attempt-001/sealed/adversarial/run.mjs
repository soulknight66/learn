import assert from "node:assert/strict";
import { loadImplementations } from "../evaluator/bindings.mjs";
import { adversarialCases } from "./cases.mjs";

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

function executeCase(api, testCase, backend) {
  try {
    const result = api.run(testCase.source, {
      backend,
      ...(testCase.maxSteps === undefined ? {} : { maxSteps: testCase.maxSteps }),
    });
    return { kind: "success", value: normalizedResult(result) };
  } catch (error) {
    return { kind: "error", error };
  }
}

function expectationFor(testCase, backend) {
  return testCase.expectedByBackend?.[backend] ?? testCase;
}

function verifyExpected(api, testCase, backend, observation, role) {
  const expectation = expectationFor(testCase, backend);
  const context = `${testCase.id} (${role}/${backend})`;
  if (expectation.expectedError !== undefined) {
    assert.equal(observation.kind, "error", `${context}: expected an error`);
    const ExpectedClass = api[expectation.expectedError.className];
    assert.equal(typeof ExpectedClass, "function", `${context}: unknown expected error class`);
    assert.ok(
      observation.error instanceof ExpectedClass,
      `${context}: wrong public error class or leaked host-language error`,
    );
    assert.equal(observation.error.code, expectation.expectedError.code, `${context}: wrong error code`);
    assert.ok(
      typeof observation.error.message === "string" && observation.error.message.length > 0,
      `${context}: missing human-readable message`,
    );
    return;
  }

  assert.equal(observation.kind, "success", `${context}: unexpected ${observation.error?.name ?? "error"}`);
  assert.deepEqual(observation.value, expectation.expected, `${context}: wrong observable result`);
}

function verifyBackendParity(testCase, tree, vm, role) {
  const context = `${testCase.id} (${role} backend parity)`;
  if (testCase.allowStepLimitDivergence === true) {
    const exhausted = [tree, vm].some(
      (item) => item.kind === "error" && item.error?.code === "STEP_LIMIT_EXCEEDED",
    );
    if (exhausted) return;
  }
  assert.equal(tree.kind, vm.kind, `${context}: completion modes differ`);
  if (tree.kind === "success") {
    assert.deepEqual(vm.value, tree.value, `${context}: results differ`);
  } else {
    assert.equal(vm.error.code, tree.error.code, `${context}: error codes differ`);
  }
}

function verifyCandidateMatchesOracle(testCase, backend, candidate, oracle) {
  const context = `${testCase.id} (candidate/oracle ${backend})`;
  assert.equal(candidate.kind, oracle.kind, `${context}: completion modes differ`);
  if (candidate.kind === "success") {
    assert.deepEqual(candidate.value, oracle.value, `${context}: results differ`);
  } else {
    assert.equal(candidate.error.code, oracle.error.code, `${context}: error codes differ`);
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
  const { candidate, oracle } = await loadImplementations({
    reportArtifacts: (artifacts) => {
      console.log(JSON.stringify({ event: "artifact-identities", artifacts }));
    },
  });

  let failures = 0;
  for (const testCase of selected) {
    const observations = {
      candidate: {
        tree: executeCase(candidate, testCase, "tree"),
        vm: executeCase(candidate, testCase, "vm"),
      },
      oracle: {
        tree: executeCase(oracle, testCase, "tree"),
        vm: executeCase(oracle, testCase, "vm"),
      },
    };
    try {
      for (const role of ["candidate", "oracle"]) {
        const api = role === "candidate" ? candidate : oracle;
        for (const backend of ["tree", "vm"]) {
          verifyExpected(api, testCase, backend, observations[role][backend], role);
        }
        verifyBackendParity(testCase, observations[role].tree, observations[role].vm, role);
      }
      for (const backend of ["tree", "vm"]) {
        verifyCandidateMatchesOracle(
          testCase,
          backend,
          observations.candidate[backend],
          observations.oracle[backend],
        );
      }
      console.log(`ok ${testCase.id}`);
    } catch (error) {
      failures += 1;
      console.error(`not ok ${testCase.id}`);
      console.error(error.stack ?? error);
    }
  }

  console.log(`${selected.length - failures}/${selected.length} candidate cases passed against oracle`);
  if (failures > 0) process.exitCode = 1;
}
