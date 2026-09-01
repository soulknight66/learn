"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");

const DEFAULT_ITERATIONS = 20_000;
const MAX_ITERATIONS = 100_000;

const target = process.argv[2]
  ? path.resolve(process.cwd(), process.argv[2])
  : path.join(__dirname, "..", "sealed", "reference", "src", "index.js");

function parseIterations(raw) {
  if (raw === undefined) return DEFAULT_ITERATIONS;
  if (!/^\d+$/.test(raw)) {
    throw new TypeError("iterations must be a base-10 integer");
  }
  const value = Number(raw);
  if (!Number.isSafeInteger(value) || value < 1 || value > MAX_ITERATIONS) {
    throw new RangeError(`iterations must be between 1 and ${MAX_ITERATIONS}`);
  }
  return value;
}

class ResponseSink {
  constructor() {
    this.statusCode = 200;
    this.headersSent = false;
    this.writableEnded = false;
    this.finished = false;
    this.bytes = 0;
    this.headers = Object.create(null);
  }

  setHeader(name, value) {
    if (this.headersSent) throw new Error("headers already sent");
    this.headers[String(name).toLowerCase()] = value;
  }

  getHeader(name) {
    return this.headers[String(name).toLowerCase()];
  }

  getHeaders() {
    return { ...this.headers };
  }

  hasHeader(name) {
    return Object.prototype.hasOwnProperty.call(this.headers, String(name).toLowerCase());
  }

  removeHeader(name) {
    if (this.headersSent) throw new Error("headers already sent");
    delete this.headers[String(name).toLowerCase()];
  }

  write(chunk, encoding) {
    if (this.writableEnded) throw new Error("write after end");
    this.headersSent = true;
    this.bytes += Buffer.isBuffer(chunk) ? chunk.length : Buffer.byteLength(String(chunk), encoding);
    return true;
  }

  end(chunk, encoding) {
    if (this.writableEnded) throw new Error("end called twice");
    if (chunk !== undefined && chunk !== null) this.write(chunk, encoding);
    this.headersSent = true;
    this.writableEnded = true;
    this.finished = true;
    return this;
  }
}

function requestFor(index) {
  if ((index & 1) === 0) {
    return {
      method: "GET",
      url: `/api/items/item-${index % 100}?tag=one&tag=two`,
      headers: Object.create(null),
    };
  }
  return { method: "GET", url: "/health", headers: Object.create(null) };
}

function makeApplication(createApplication) {
  const app = createApplication();
  app.use("/api", (req, res, next) => next());
  app.get("/health", (req, res) => res.type("text/plain").send("ok"));
  app.get("/api/items/:id", (req, res) => {
    res.json({ id: req.params.id, tags: req.query.tag });
  });
  return app;
}

function dispatchBatch(app, count) {
  let checksum = 0;
  for (let index = 0; index < count; index += 1) {
    const req = requestFor(index);
    const res = new ResponseSink();
    app(req, res);
    assert.equal(
      res.writableEnded,
      true,
      "benchmark handlers must complete synchronously for this in-process measurement",
    );
    checksum = (checksum + res.statusCode + res.bytes) >>> 0;
  }
  return checksum;
}

function main() {
  const iterations = parseIterations(process.argv[3]);
  const warmupIterations = Math.min(2_000, Math.max(100, Math.ceil(iterations / 10)));

  // The target is an explicit local harness input.
  // eslint-disable-next-line global-require, import/no-dynamic-require
  const implementation = require(target);
  assert.equal(typeof implementation, "function", "target must export createApplication directly");
  const app = makeApplication(implementation);

  dispatchBatch(app, warmupIterations);
  const started = process.hrtime.bigint();
  const checksum = dispatchBatch(app, iterations);
  const elapsedNanoseconds = process.hrtime.bigint() - started;
  const elapsedMs = Number(elapsedNanoseconds) / 1e6;
  const requestsPerSecond = iterations / (elapsedMs / 1000);

  const report = {
    target: path.relative(process.cwd(), target) || ".",
    node: process.version,
    warmupIterations,
    iterations,
    elapsedMs: Number(elapsedMs.toFixed(3)),
    requestsPerSecond: Number(requestsPerSecond.toFixed(1)),
    checksum,
  };
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}

try {
  main();
} catch (error) {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
}
