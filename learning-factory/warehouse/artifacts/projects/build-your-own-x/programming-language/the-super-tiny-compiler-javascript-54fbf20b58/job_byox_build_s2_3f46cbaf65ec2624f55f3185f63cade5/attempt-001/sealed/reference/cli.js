#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { compile, interpret, CompilerError } = require('./compiler.js');

function usage() {
  process.stderr.write('usage: node sealed/reference/cli.js [--emit-js] PROGRAM.ripple\n');
}

function main(argv) {
  const emitJavaScript = argv[0] === '--emit-js';
  const fileArgument = emitJavaScript ? argv[1] : argv[0];
  if (!fileArgument || argv.length !== (emitJavaScript ? 2 : 1)) {
    usage();
    return 2;
  }
  const filename = path.resolve(fileArgument);
  const source = fs.readFileSync(filename, 'utf8');
  if (emitJavaScript) {
    process.stdout.write(compile(source));
  } else {
    for (const value of interpret(source)) {
      process.stdout.write(`${JSON.stringify(value)}\n`);
    }
  }
  return 0;
}

try {
  process.exitCode = main(process.argv.slice(2));
} catch (error) {
  if (error instanceof CompilerError) {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  } else {
    throw error;
  }
}
