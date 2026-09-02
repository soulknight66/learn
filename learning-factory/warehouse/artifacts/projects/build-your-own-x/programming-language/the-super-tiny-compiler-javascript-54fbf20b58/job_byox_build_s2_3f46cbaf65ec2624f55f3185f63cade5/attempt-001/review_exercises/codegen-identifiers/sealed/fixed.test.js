'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { generatedName, emitDeclaration, emitRead } = require('./fixed.js');

test('declarations and reads share opaque generated names', () => {
  assert.equal(emitDeclaration(7, '40 + 2'), 'const v_7 = 40 + 2;');
  assert.equal(emitRead(7), 'v_7');
});

test('only non-negative safe integer IDs reach syntax', () => {
  for (const value of [-1, 1.5, NaN, Infinity, '1', '0; throw 1']) {
    assert.throws(() => generatedName(value), /bindingId/);
  }
});
