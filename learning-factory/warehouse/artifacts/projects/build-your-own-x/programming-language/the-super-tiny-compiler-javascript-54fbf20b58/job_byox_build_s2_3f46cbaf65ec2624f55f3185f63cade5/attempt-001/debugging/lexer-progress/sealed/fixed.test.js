'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { scan } = require('./fixed.js');

for (const punctuation of ['(', ')', ',', ';']) {
  test(`consumes ${punctuation}`, () => {
    assert.deepEqual(scan(punctuation), [{
      kind: 'PUNCTUATION', value: punctuation, offset: 0,
    }]);
  });
}

test('consumes a mixed sequence and preserves original offsets', () => {
  assert.deepEqual(scan('(,);'), [
    { kind: 'PUNCTUATION', value: '(', offset: 0 },
    { kind: 'PUNCTUATION', value: ',', offset: 1 },
    { kind: 'PUNCTUATION', value: ')', offset: 2 },
    { kind: 'PUNCTUATION', value: ';', offset: 3 },
  ]);
});
