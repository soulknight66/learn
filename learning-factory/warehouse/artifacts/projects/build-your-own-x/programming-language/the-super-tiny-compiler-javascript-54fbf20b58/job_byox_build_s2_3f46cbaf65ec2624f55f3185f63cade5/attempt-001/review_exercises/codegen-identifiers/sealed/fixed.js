'use strict';

function generatedName(bindingId) {
  if (!Number.isSafeInteger(bindingId) || bindingId < 0) {
    throw new TypeError('bindingId must be a non-negative safe integer');
  }
  return `v_${bindingId}`;
}

function emitDeclaration(bindingId, numericExpression) {
  return `const ${generatedName(bindingId)} = ${numericExpression};`;
}

function emitRead(bindingId) {
  return generatedName(bindingId);
}

module.exports = { generatedName, emitDeclaration, emitRead };
