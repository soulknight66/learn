"use strict";

const assert = require("node:assert/strict");
const { install } = require("./flawed-response");

function response(method = "GET") {
  const headers = Object.create(null);
  const res = {
    statusCode: 200,
    chunks: [],
    setHeader(name, value) {
      headers[String(name).toLowerCase()] = String(value);
    },
    getHeader(name) {
      return headers[String(name).toLowerCase()];
    },
    end(chunk) {
      if (chunk !== undefined) this.chunks.push(Buffer.from(chunk));
    },
  };
  return install({ method }, res);
}

function body(res) {
  return Buffer.concat(res.chunks);
}

const falsy = response();
falsy.send(false);

const unicode = response();
unicode.send("☃");

const head = response("HEAD");
head.send("metadata only");

const invalidStatus = response();
let invalidStatusThrew = false;
try {
  invalidStatus.status(0);
} catch (error) {
  void error;
  invalidStatusThrew = true;
}

const observed = {
  falsyBody: body(falsy).toString("utf8"),
  unicodeAdvertisedBytes: Number(unicode.getHeader("content-length")),
  unicodeActualBytes: body(unicode).length,
  headBytes: body(head).length,
  invalidStatusThrew,
};
const intended = {
  falsyBody: "false",
  unicodeAdvertisedBytes: 3,
  unicodeActualBytes: 3,
  headBytes: 0,
  invalidStatusThrew: true,
};

try {
  assert.deepEqual(observed, intended);
  process.stdout.write("PASS response helper observations satisfy the proposed contract\n");
} catch (error) {
  process.stderr.write(`REVIEW NEEDED\nobserved: ${JSON.stringify(observed)}\n`);
  process.stderr.write(`intended: ${JSON.stringify(intended)}\n`);
  process.exitCode = 1;
}
