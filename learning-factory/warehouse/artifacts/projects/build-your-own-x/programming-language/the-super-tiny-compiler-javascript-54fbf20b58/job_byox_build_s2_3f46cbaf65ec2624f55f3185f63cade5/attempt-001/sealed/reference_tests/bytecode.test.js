'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { interpret } = require('../reference/compiler.js');
const { compileBytecode, runBytecode } = require('../alternatives/bytecode.js');

test('bytecode backend agrees with the tree interpreter', () => {
  const programs = [
    'emit 2 + 3 * 4;',
    'let x = 7; emit pow(x, 2);',
    'emit max(1, 9, 3); emit len("🙂a");',
    'emit 3 == "3"; emit 3 != "3";',
  ];
  for (const source of programs) {
    assert.deepEqual(runBytecode(compileBytecode(source)), interpret(source));
  }
});

test('bytecode jumps implement operand-valued short circuiting', () => {
  const source = 'emit false && len(2); emit "yes" || len(2);';
  const bytecode = compileBytecode(source);
  assert.ok(bytecode.some(({ op }) => op === 'JUMP_IF_FALSE'));
  assert.ok(bytecode.some(({ op }) => op === 'JUMP_IF_TRUE'));
  assert.deepEqual(runBytecode(bytecode), [false, 'yes']);
});

test('VM rejects invalid programs and enforces a step budget', () => {
  assert.throws(() => runBytecode([{ op: 'POP' }, { op: 'HALT' }]), /stack underflow/);
  assert.throws(() => runBytecode([{ op: 'NOPE' }]), /invalid bytecode opcode/);
  assert.throws(
    () => runBytecode([{ op: 'PUSH', argument: true }, { op: 'JUMP_IF_TRUE', argument: 0 }], { maxSteps: 5 }),
    /step limit exceeded/,
  );
});
