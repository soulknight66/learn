'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { scan } = require('./buggy.js');

test('scanner consumes all punctuation', () => {
  assert.deepEqual(
    scan('(,);'),
    ['(', ',', ')', ';'].map((value, offset) => ({
      kind: 'PUNCTUATION', value, offset,
    })),
  );
});

test('scanner reports the position of unknown input', () => {
  assert.throws(
    () => scan('  @'),
    (error) => error.code === 'UNEXPECTED_CHARACTER' && error.offset === 2,
  );
});
