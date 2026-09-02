'use strict';

const http = require('node:http');

function integerSetting(name, fallback, minimum, maximum) {
  const raw = process.env[name];
  const value = raw === undefined ? fallback : Number(raw);
  if (!Number.isSafeInteger(value) || value < minimum || value > maximum) {
    throw new Error(`${name} must be an integer from ${minimum} through ${maximum}`);
  }
  return value;
}

const target = new URL(process.env.TARGET_URL || 'http://127.0.0.1:3000/health');
if (target.protocol !== 'http:' || !['127.0.0.1', 'localhost', '::1'].includes(target.hostname)) {
  throw new Error('TARGET_URL must use HTTP on a loopback host');
}

const durationMs = integerSetting('DURATION_MS', 5000, 100, 60000);
const concurrency = integerSetting('CONCURRENCY', 16, 1, 256);
const deadline = Date.now() + durationMs;
const latencies = [];
let succeeded = 0;
let failed = 0;

function once() {
  const started = process.hrtime.bigint();
  return new Promise((resolve) => {
    const req = http.get(target, (res) => {
      res.resume();
      res.once('end', () => {
        const elapsed = Number(process.hrtime.bigint() - started) / 1e6;
        latencies.push(elapsed);
        if (res.statusCode >= 200 && res.statusCode < 400) {
          succeeded += 1;
        } else {
          failed += 1;
        }
        resolve();
      });
      res.once('error', () => {
        failed += 1;
        resolve();
      });
    });
    req.setTimeout(2000, () => req.destroy(new Error('benchmark request timed out')));
    req.once('error', () => {
      failed += 1;
      resolve();
    });
  });
}

async function worker() {
  while (Date.now() < deadline) {
    await once();
  }
}

function percentile(sorted, fraction) {
  if (sorted.length === 0) {
    return null;
  }
  const index = Math.min(sorted.length - 1, Math.ceil(sorted.length * fraction) - 1);
  return Number(sorted[index].toFixed(3));
}

Promise.all(Array.from({ length: concurrency }, worker))
  .then(() => {
    latencies.sort((left, right) => left - right);
    process.stdout.write(`${JSON.stringify({
      target: target.href,
      configuredDurationMs: durationMs,
      concurrency,
      succeeded,
      failed,
      latencyMs: {
        p50: percentile(latencies, 0.50),
        p95: percentile(latencies, 0.95),
        p99: percentile(latencies, 0.99)
      }
    }, null, 2)}\n`);
    if (failed > 0) {
      process.exitCode = 1;
    }
  })
  .catch((error) => {
    process.stderr.write(`${error.stack || error.message}\n`);
    process.exitCode = 1;
  });
