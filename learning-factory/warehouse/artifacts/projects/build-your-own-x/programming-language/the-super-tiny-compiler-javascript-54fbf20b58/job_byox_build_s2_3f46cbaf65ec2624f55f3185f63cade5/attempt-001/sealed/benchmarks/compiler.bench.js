#!/usr/bin/env node
'use strict';

const { parse, tokenize, compile, interpret } = require('../reference/compiler.js');

function positiveInteger(raw, fallback, name) {
  if (raw === undefined) return fallback;
  const value = Number(raw);
  if (!Number.isSafeInteger(value) || value < 1) {
    throw new RangeError(`${name} must be a positive safe integer`);
  }
  return value;
}

function makeProgram(size) {
  const lines = ['let v0 = 1;'];
  for (let index = 1; index < size; index += 1) {
    lines.push(`let v${index} = v${index - 1} + 1;`);
  }
  lines.push(`emit v${size - 1};`);
  return `${lines.join('\n')}\n`;
}

function time(iterations, operation) {
  const start = process.hrtime.bigint();
  for (let index = 0; index < iterations; index += 1) operation();
  const elapsed = process.hrtime.bigint() - start;
  return Number(elapsed) / 1e6;
}

const size = positiveInteger(process.argv[2], 200, 'size');
const iterations = positiveInteger(process.argv[3], 25, 'iterations');
const source = makeProgram(size);

for (let index = 0; index < 5; index += 1) {
  compile(source);
  const output = interpret(source);
  if (output.length !== 1 || output[0] !== size) throw new Error('warmup result mismatch');
}

const generated = compile(source);
const executeGenerated = Function(generated);
const generatedResult = executeGenerated();
if (generatedResult.length !== 1 || generatedResult[0] !== size) {
  throw new Error('generated result mismatch');
}

const measurements = {
  tokenize_and_parse_ms: time(iterations, () => parse(tokenize(source))),
  optimized_compile_ms: time(iterations, () => compile(source)),
  interpret_ms: time(iterations, () => {
    const result = interpret(source);
    if (result[0] !== size) throw new Error('interpreter result mismatch');
  }),
  execute_generated_ms: time(iterations, () => {
    const result = executeGenerated();
    if (result[0] !== size) throw new Error('generated result mismatch');
  }),
};

process.stdout.write(`${JSON.stringify({
  node: process.version,
  platform: process.platform,
  architecture: process.arch,
  declarations: size,
  source_bytes: Buffer.byteLength(source),
  iterations,
  warmups: 5,
  measurements,
}, null, 2)}\n`);
