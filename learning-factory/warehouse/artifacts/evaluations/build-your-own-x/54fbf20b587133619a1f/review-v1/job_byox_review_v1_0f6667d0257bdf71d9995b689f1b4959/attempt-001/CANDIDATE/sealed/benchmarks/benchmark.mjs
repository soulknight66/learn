import { performance } from "node:perf_hooks";
import process from "node:process";
import {
  compile,
  evaluate,
  execute,
  parse,
  run,
  tokenize,
} from "../reference/index.js";

function arithmeticSource(terms) {
  const expression = Array.from({ length: terms }, (_, index) => String((index % 9) + 1)).join(" + ");
  const expected = Array.from({ length: terms }, (_, index) => (index % 9) + 1)
    .reduce((sum, value) => sum + value, 0);
  return { source: `emit ${expression};`, expected: [expected] };
}

function loopSource(iterations) {
  return {
    source: `
      let index = 0;
      let total = 0;
      while index < ${iterations} {
        set total = total + index;
        set index = index + 1;
      }
      emit total;
    `,
    expected: [iterations * (iterations - 1) / 2],
  };
}

function branchSource(iterations) {
  const midpoint = Math.floor(iterations / 2);
  return {
    source: `
      let index = 0;
      let score = 0;
      while index < ${iterations} {
        if index < ${midpoint} {
          set score = score + 1;
        } else {
          set score = score + 2;
        }
        set index = index + 1;
      }
      emit score;
    `,
    expected: [midpoint + (iterations - midpoint) * 2],
  };
}

const workloadDefinitions = [
  { name: "arithmetic-96-terms", ...arithmeticSource(96) },
  { name: "counted-loop-200", ...loopSource(200) },
  { name: "branch-loop-180", ...branchSource(180) },
];

function positiveInteger(text, flag, { allowZero = false } = {}) {
  const value = Number(text);
  const minimum = allowZero ? 0 : 1;
  if (!Number.isSafeInteger(value) || value < minimum) {
    throw new Error(`${flag} must be a ${allowZero ? "non-negative" : "positive"} safe integer`);
  }
  return value;
}

function readOptions(arguments_) {
  const options = { samples: 9, iterations: 50, warmup: 15 };
  for (let index = 0; index < arguments_.length; index += 2) {
    const flag = arguments_[index];
    const text = arguments_[index + 1];
    if (text === undefined) throw new Error(`missing value for ${flag}`);
    if (flag === "--samples") options.samples = positiveInteger(text, flag);
    else if (flag === "--iterations") options.iterations = positiveInteger(text, flag);
    else if (flag === "--warmup") options.warmup = positiveInteger(text, flag, { allowZero: true });
    else throw new Error(`unknown option ${flag}`);
  }
  return options;
}

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value !== null && typeof value === "object") {
    const entries = Object.entries(value)
      .sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0))
      .map(([key, item]) => [key, stable(item)]);
    return Object.fromEntries(entries);
  }
  return value;
}

function sameValue(actual, expected) {
  return JSON.stringify(stable(actual)) === JSON.stringify(stable(expected));
}

function prepare(definition) {
  const tokens = tokenize(definition.source);
  const ast = parse(tokens);
  const bytecode = compile(ast);
  const tree = evaluate(ast, { maxSteps: 100_000 });
  const vm = execute(bytecode, { maxSteps: 100_000 });
  if (!sameValue(tree, definition.expected)) {
    throw new Error(`${definition.name}: tree result failed correctness gate`);
  }
  if (!sameValue(vm, definition.expected)) {
    throw new Error(`${definition.name}: VM result failed correctness gate`);
  }

  return {
    ...definition,
    tokens,
    ast,
    bytecode,
    operations: [
      { name: "tokenize", perform: () => tokenize(definition.source) },
      { name: "parse-pretokenized", perform: () => parse(tokens) },
      { name: "compile-ast", perform: () => compile(ast) },
      { name: "evaluate-ast", perform: () => evaluate(ast, { maxSteps: 100_000 }) },
      { name: "execute-bytecode", perform: () => execute(bytecode, { maxSteps: 100_000 }) },
      { name: "run-tree-pipeline", perform: () => run(definition.source, { backend: "tree", maxSteps: 100_000 }) },
      { name: "run-vm-pipeline", perform: () => run(definition.source, { backend: "vm", maxSteps: 100_000 }) },
    ],
  };
}

let sink = 0;
function consume(value) {
  if (Array.isArray(value)) sink ^= value.length;
  else if (value !== null && typeof value === "object") sink ^= Object.keys(value).length;
  else sink ^= Number(Boolean(value));
}

function invoke(operation, count) {
  for (let iteration = 0; iteration < count; iteration += 1) {
    consume(operation.perform());
  }
}

function summarize(samples) {
  const sorted = [...samples].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  const median = sorted.length % 2 === 1
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2;
  return {
    minimumMs: sorted[0],
    medianMs: median,
    meanMs: sorted.reduce((sum, value) => sum + value, 0) / sorted.length,
    maximumMs: sorted.at(-1),
  };
}

function measure(workload, options) {
  for (const operation of workload.operations) invoke(operation, options.warmup);

  const samplesByOperation = new Map(workload.operations.map(({ name }) => [name, []]));
  for (let sample = 0; sample < options.samples; sample += 1) {
    // Rotate a deterministic order to reduce a fixed first/last-position bias.
    const ordered = workload.operations.map((_, offset) => workload.operations[(sample + offset) % workload.operations.length]);
    for (const operation of ordered) {
      const started = performance.now();
      invoke(operation, options.iterations);
      const elapsed = performance.now() - started;
      samplesByOperation.get(operation.name).push(elapsed);
    }
  }

  return Object.fromEntries(workload.operations.map(({ name }) => {
    const samplesMs = samplesByOperation.get(name);
    return [name, { samplesMs, ...summarize(samplesMs) }];
  }));
}

let options;
try {
  options = readOptions(process.argv.slice(2));
} catch (error) {
  console.error(error.message);
  console.error("usage: node sealed/benchmarks/benchmark.mjs [--samples N] [--iterations N] [--warmup N]");
  process.exit(2);
}

const prepared = workloadDefinitions.map(prepare);
const results = Object.fromEntries(prepared.map((workload) => [workload.name, measure(workload, options)]));
const report = {
  disclaimer: "Observed harness timings for this invocation only; not a production or cross-machine performance claim.",
  runtime: {
    node: process.version,
    platform: process.platform,
    architecture: process.arch,
  },
  settings: {
    ...options,
    durationUnit: "milliseconds per sample batch",
    correctnessGate: "tree and VM matched sealed expected observations before timing",
  },
  results,
  sink,
};

console.log(JSON.stringify(report, null, 2));
