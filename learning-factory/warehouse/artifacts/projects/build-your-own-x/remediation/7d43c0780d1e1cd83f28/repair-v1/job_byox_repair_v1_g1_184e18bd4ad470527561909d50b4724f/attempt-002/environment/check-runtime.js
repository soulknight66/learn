'use strict';

const minimum = [18, 17, 0];
const current = process.versions.node.split('.').map(Number);

function isAtLeast(actual, required) {
  for (let index = 0; index < required.length; index += 1) {
    if (actual[index] > required[index]) return true;
    if (actual[index] < required[index]) return false;
  }
  return true;
}

if (!isAtLeast(current, minimum)) {
  console.error(`Node ${process.versions.node} is unsupported; use Node >=18.17.0.`);
  process.exitCode = 1;
} else {
  console.log(`Node ${process.versions.node} is supported.`);
}

