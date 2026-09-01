"use strict";

const assert = require("node:assert/strict");
const { respond } = require("./src/respond");

function mockResponse() {
  const headers = Object.create(null);
  return {
    statusCode: 0,
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
}

const unicode = mockResponse();
respond({ method: "GET" }, unicode, "snowman: ☃");
const unicodeBody = Buffer.concat(unicode.chunks);

const head = mockResponse();
respond({ method: "HEAD" }, head, "representation");

const observed = {
  unicodeAdvertisedBytes: Number(unicode.getHeader("content-length")),
  unicodeActualBytes: unicodeBody.length,
  headAdvertisedBytes: Number(head.getHeader("content-length")),
  headActualBytes: Buffer.concat(head.chunks).length,
};
const intended = {
  unicodeAdvertisedBytes: Buffer.byteLength("snowman: ☃"),
  unicodeActualBytes: Buffer.byteLength("snowman: ☃"),
  headAdvertisedBytes: Buffer.byteLength("representation"),
  headActualBytes: 0,
};

try {
  assert.deepEqual(observed, intended);
  process.stdout.write("PASS response metadata and wire payload agree\n");
} catch (error) {
  process.stderr.write(`FAIL response metadata and wire payload disagree\n`);
  process.stderr.write(`observed: ${JSON.stringify(observed)}\n`);
  process.stderr.write(`intended: ${JSON.stringify(intended)}\n`);
  process.exitCode = 1;
}
