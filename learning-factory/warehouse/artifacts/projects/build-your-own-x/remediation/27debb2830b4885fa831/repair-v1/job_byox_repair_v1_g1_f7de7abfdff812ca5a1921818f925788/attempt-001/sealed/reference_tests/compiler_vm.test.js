import test from "node:test";
import assert from "node:assert/strict";
import {
  tokenize, parse, compile, runBytecode, BytecodeError, CompileError
} from "../reference/src/index.js";

const loc = { line: 1, column: 1 };

test("compiler emits bytecode with balanced branch and loop joins", () => {
  const ast = parse(tokenize("let x = 2; while (x > 0) { x = x - 1; } if (x == 0) { 9; } else { 8; }"));
  const program = compile(ast);
  assert.equal(program.version, 1);
  assert.equal(program.code.filter(({ op }) => op === "HALT").length, 1);
  assert.equal(program.code.at(-1).op, "HALT");
  assert.deepEqual(runBytecode(program), { value: 9, output: [] });
});

test("compiler rejects malformed AST nodes and locations", () => {
  assert.throws(() => compile({ type: "Program", body: [{ type: "Mystery", loc }], loc }), CompileError);
  assert.throws(() => compile({ type: "Program", body: [], loc: { line: 0, column: 1 } }), CompileError);
});

test("validator rejects structural and argument errors", () => {
  const failures = [
    null,
    { version: 2, constants: [], code: [{ op: "HALT", loc }] },
    { version: 1, constants: [Infinity], code: [{ op: "NULL", loc }, { op: "HALT", loc }] },
    { version: 1, constants: [], code: [{ op: "MYSTERY", loc }, { op: "HALT", loc }] },
    { version: 1, constants: [], code: [{ op: "NULL", arg: 1, loc }, { op: "HALT", loc }] },
    { version: 1, constants: [], code: [{ op: "JUMP", arg: 8, loc }, { op: "HALT", loc }] },
    { version: 1, constants: [], code: [{ op: "HALT", loc }, { op: "HALT", loc }] }
  ];
  for (const program of failures) assert.throws(() => runBytecode(program), BytecodeError);
});

test("validator performs abstract stack and scope analysis", () => {
  const failures = [
    { version: 1, constants: [], code: [{ op: "POP", loc }, { op: "HALT", loc }] },
    { version: 1, constants: [], code: [{ op: "NULL", loc }, { op: "EXIT_SCOPE", loc }, { op: "HALT", loc }] },
    {
      version: 1,
      constants: [],
      code: [
        { op: "TRUE", loc },
        { op: "JUMP_IF_FALSE", arg: 3, loc },
        { op: "NULL", loc },
        { op: "HALT", loc }
      ]
    }
  ];
  for (const program of failures) assert.throws(() => runBytecode(program), BytecodeError);
});

test("bytecode is validated completely before any dispatch", () => {
  const program = {
    version: 1,
    constants: [],
    code: [
      { op: "NULL", loc },
      { op: "PRINT", loc },
      { op: "UNKNOWN", loc },
      { op: "HALT", loc }
    ]
  };
  assert.throws(() => runBytecode(program), BytecodeError);
});

test("validator rejects sparse arrays and accessor-bearing records", () => {
  const sparseConstants = [];
  sparseConstants.length = 1;
  assert.throws(() => runBytecode({
    version: 1,
    constants: sparseConstants,
    code: [{ op: "NULL", loc }, { op: "HALT", loc }]
  }), BytecodeError);

  let getterCalled = false;
  const instruction = { loc };
  Object.defineProperty(instruction, "op", {
    enumerable: true,
    get() { getterCalled = true; return "NULL"; }
  });
  assert.throws(() => runBytecode({
    version: 1,
    constants: [],
    code: [instruction, { op: "HALT", loc }]
  }), BytecodeError);
  assert.equal(getterCalled, false);
});

test("validator rejects non-intrinsic array prototypes without inherited effects", () => {
  const haltProgram = (code) => ({ version: 1, constants: [], code });
  const instructions = () => [{ op: "NULL", loc }, { op: "HALT", loc }];

  let inheritedAccesses = 0;
  const customPrototype = Object.create(Array.prototype);
  Object.defineProperty(customPrototype, "at", {
    get() {
      inheritedAccesses += 1;
      return () => ({ op: "HALT", loc });
    }
  });
  const custom = instructions();
  Object.setPrototypeOf(custom, customPrototype);
  assert.throws(() => runBytecode(haltProgram(custom)), BytecodeError);
  assert.equal(inheritedAccesses, 0);

  const nullPrototype = instructions();
  Object.setPrototypeOf(nullPrototype, null);
  assert.throws(() => runBytecode(haltProgram(nullPrototype)), BytecodeError);

  class InstructionArray extends Array {}
  const subclass = new InstructionArray(...instructions());
  assert.throws(() => runBytecode(haltProgram(subclass)), BytecodeError);

  const customConstants = [];
  Object.setPrototypeOf(customConstants, customPrototype);
  assert.throws(() => runBytecode({
    version: 1,
    constants: customConstants,
    code: instructions()
  }), BytecodeError);
  assert.equal(inheritedAccesses, 0);
});
