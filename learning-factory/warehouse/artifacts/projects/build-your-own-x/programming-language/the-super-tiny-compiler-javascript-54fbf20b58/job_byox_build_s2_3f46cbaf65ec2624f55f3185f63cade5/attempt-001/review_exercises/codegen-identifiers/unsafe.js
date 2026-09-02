'use strict';

function emitDeclaration(name, numericExpression) {
  return `const ${name} = ${numericExpression};`;
}

function emitRead(name) {
  return name;
}

module.exports = { emitDeclaration, emitRead };
