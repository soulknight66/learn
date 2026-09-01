"use strict";

const assert = require("node:assert/strict");
const { run } = require("./src/router");

let middleVisits = 0;
let finalVisits = 0;
let doneCalls = 0;

run(
  [
    (req, res, next) => {
      void req;
      void res;
      next();
      next();
    },
    (req, res, next) => {
      void req;
      void res;
      middleVisits += 1;
      next();
    },
    (req, res, next) => {
      void req;
      void res;
      finalVisits += 1;
      next();
    },
  ],
  {},
  {},
  (error) => {
    assert.equal(error, undefined);
    doneCalls += 1;
  },
);

try {
  assert.equal(middleVisits, 1, "middle middleware must run once");
  assert.equal(finalVisits, 1, "final middleware must run once");
  assert.equal(doneCalls, 1, "completion must be owned by one dispatch branch");
  process.stdout.write("PASS dispatcher advances once per handler invocation\n");
} catch (error) {
  process.stderr.write(`FAIL ${error.message}\n`);
  process.exitCode = 1;
}
