import { performance } from "node:perf_hooks";

const requested = process.argv[2] ?? "../starter/src/index.js";
const moduleUrl = new URL(requested, import.meta.url);
const implementation = await import(moduleUrl);
if (typeof implementation.execute !== "function") {
  throw new TypeError("Benchmark target must export execute");
}

const source = `
  let total = 0;
  let n = 200;
  while (n > 0) {
    total = total + n;
    n = n - 1;
  }
  total;
`;
const warmups = 10;
const samples = 25;
const executionsPerSample = 20;

for (const engine of ["tree", "vm"]) {
  for (let i = 0; i < warmups; i += 1) implementation.execute(source, { engine });
}

const results = {};
for (const engine of ["tree", "vm"]) {
  results[engine] = [];
  for (let sample = 0; sample < samples; sample += 1) {
    const started = performance.now();
    for (let i = 0; i < executionsPerSample; i += 1) {
      const result = implementation.execute(source, { engine });
      if (result.value !== 20100 || result.output.length !== 0) throw new Error("Incorrect benchmark result");
    }
    results[engine].push(performance.now() - started);
  }
}

console.log(JSON.stringify({
  node: process.versions.node,
  platform: process.platform,
  architecture: process.arch,
  warmups,
  samples,
  executions_per_sample: executionsPerSample,
  duration_unit: "milliseconds",
  raw_durations: results
}, null, 2));
