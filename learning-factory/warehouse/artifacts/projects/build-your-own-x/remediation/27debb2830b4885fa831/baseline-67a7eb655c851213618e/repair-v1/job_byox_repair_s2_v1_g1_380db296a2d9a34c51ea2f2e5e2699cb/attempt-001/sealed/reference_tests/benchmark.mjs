import { performance } from "node:perf_hooks";

import { execute } from "../reference/src/pipeline.mjs";

const source = "let x = 1; { let y = x * 3; x = y + 2; } if (x >= 5) { x * 2; } else { 0; }";
const iterations = 10_000;
const results = {};

for (const backend of ["tree", "vm"]) {
  const start = performance.now();
  let checksum = 0;
  for (let index = 0; index < iterations; index += 1) {
    checksum += execute(source, { backend }).value;
  }
  results[backend] = { elapsedMilliseconds: performance.now() - start, checksum };
}

console.log(JSON.stringify({ iterations, results }, null, 2));
