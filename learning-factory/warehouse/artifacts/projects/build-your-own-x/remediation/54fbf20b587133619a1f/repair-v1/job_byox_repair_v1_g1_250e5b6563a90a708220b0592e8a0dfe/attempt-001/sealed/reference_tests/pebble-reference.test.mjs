import test from "node:test";
import assert from "node:assert/strict";

import {
  BYTECODE_FORMAT,
  BYTECODE_VERSION,
  BytecodeError,
  CompileError,
  DEFAULT_MAX_STEPS,
  LexerError,
  OpCode,
  ParseError,
  PebbleRuntimeError,
  PebbleStepLimitError,
  PebbleSyntaxError,
  RuntimeError,
  StepLimitError,
  TokenType,
  compile,
  evaluate,
  execute,
  parse,
  run,
  tokenize,
} from "../reference/index.js";

function captureError(action) {
  try {
    action();
  } catch (error) {
    return error;
  }
  assert.fail("expected action to throw");
}

function assertBackendsAgree(source, expected) {
  const tree = evaluate(source);
  const vm = execute(compile(source));
  assert.deepEqual(vm, tree);
  if (expected !== undefined) assert.deepEqual(tree, expected);
  return tree;
}

function bytecode(constants, instructions) {
  return {
    format: BYTECODE_FORMAT,
    version: BYTECODE_VERSION,
    constants,
    instructions,
  };
}

test("tokenizer exposes exact token records, positions, comments, and longest operators", () => {
  const source = "// heading\r\nlet alpha_2 = 12.50 != 4; // tail\nemit !false;";
  const tokens = tokenize(source);

  assert.deepEqual(tokens.map((token) => token.type), [
    TokenType.LET,
    TokenType.IDENTIFIER,
    TokenType.EQUAL,
    TokenType.NUMBER,
    TokenType.BANG_EQUAL,
    TokenType.NUMBER,
    TokenType.SEMICOLON,
    TokenType.EMIT,
    TokenType.BANG,
    TokenType.FALSE,
    TokenType.SEMICOLON,
    TokenType.EOF,
  ]);
  assert.deepEqual(tokens[0], {
    type: "LET",
    lexeme: "let",
    literal: null,
    line: 2,
    column: 1,
  });
  assert.deepEqual(tokens[3], {
    type: "NUMBER",
    lexeme: "12.50",
    literal: 12.5,
    line: 2,
    column: 15,
  });
  assert.deepEqual(tokens[9], {
    type: "FALSE",
    lexeme: "false",
    literal: false,
    line: 3,
    column: 7,
  });
  assert.deepEqual(tokens.at(-1), {
    type: "EOF",
    lexeme: "",
    literal: null,
    line: 3,
    column: 13,
  });
  for (const token of tokens) {
    assert.deepEqual(Object.keys(token), ["type", "lexeme", "literal", "line", "column"]);
  }
});

test("tokenizer applies the documented ASCII number and identifier rules", () => {
  const identifiers = tokenize("let constructor = 1; let __proto__ = 2;");
  assert.equal(identifiers[1].type, TokenType.IDENTIFIER);
  assert.equal(identifiers[6].type, TokenType.IDENTIFIER);

  const dot = captureError(() => tokenize("emit 1.;"));
  assert.ok(dot instanceof LexerError);
  assert.ok(dot instanceof PebbleSyntaxError);
  assert.equal(dot.code, "UNEXPECTED_CHARACTER");
  assert.equal(dot.line, 1);
  assert.equal(dot.column, 7);

  const huge = captureError(() => tokenize(`emit ${"9".repeat(400)};`));
  assert.ok(huge instanceof LexerError);
  assert.equal(huge.code, "INVALID_NUMBER");
});

test("parser returns the exact public AST and honors precedence", () => {
  const source = [
    "let x = 1 + 2 * 3;",
    "set x = -(x - 4);",
    "if x >= 0 == true { emit x; } else { emit false; }",
  ].join("\n");
  const expected = {
    type: "Program",
    body: [
      {
        type: "LetStatement",
        name: "x",
        initializer: {
          type: "BinaryExpression",
          operator: "+",
          left: { type: "NumberLiteral", value: 1 },
          right: {
            type: "BinaryExpression",
            operator: "*",
            left: { type: "NumberLiteral", value: 2 },
            right: { type: "NumberLiteral", value: 3 },
          },
        },
      },
      {
        type: "SetStatement",
        name: "x",
        value: {
          type: "UnaryExpression",
          operator: "-",
          argument: {
            type: "BinaryExpression",
            operator: "-",
            left: { type: "Identifier", name: "x" },
            right: { type: "NumberLiteral", value: 4 },
          },
        },
      },
      {
        type: "IfStatement",
        condition: {
          type: "BinaryExpression",
          operator: "==",
          left: {
            type: "BinaryExpression",
            operator: ">=",
            left: { type: "Identifier", name: "x" },
            right: { type: "NumberLiteral", value: 0 },
          },
          right: { type: "BooleanLiteral", value: true },
        },
        consequent: {
          type: "BlockStatement",
          body: [{ type: "EmitStatement", expression: { type: "Identifier", name: "x" } }],
        },
        alternate: {
          type: "BlockStatement",
          body: [{ type: "EmitStatement", expression: { type: "BooleanLiteral", value: false } }],
        },
      },
    ],
  };

  assert.deepEqual(parse(source), expected);
  assert.deepEqual(parse(tokenize(source)), expected);
});

test("parser reports deterministic syntax errors and permits an omitted else", () => {
  for (const source of [
    "let x = 1",
    "if true { emit 1; } else",
    "while true { emit 1;",
    "emit ;",
  ]) {
    const error = captureError(() => parse(source));
    assert.ok(error instanceof ParseError);
    assert.ok(error instanceof PebbleSyntaxError);
    assert.equal(error.code, "UNEXPECTED_TOKEN");
    assert.ok(Number.isInteger(error.line));
    assert.ok(Number.isInteger(error.column));
  }

  const noEof = tokenize("emit 1;").slice(0, -1);
  assert.throws(() => parse(noEof), ParseError);

  assert.deepEqual(parse("if false { emit 1; }").body[0].alternate, null);
});

test("tree interpreter and VM agree on arithmetic, unary, comparison, and equality", () => {
  assertBackendsAgree(
    [
      "emit 1 + 2 * 3;",
      "emit (1 + 2) * 3;",
      "emit -4 / 2;",
      "emit !false;",
      "emit 3 >= 3;",
      "emit true == false;",
      "emit 1 != true;",
    ].join("\n"),
    [7, 9, -2, true, true, false, true],
  );
});

test("control flow, assignment, emits, and program-wide bindings have backend parity", () => {
  const source = `
    let n = 0;
    let sum = 0;
    while n < 5 {
      set n = n + 1;
      if n == 3 { emit false; } else { set sum = sum + n; }
    }
    emit sum;
    if sum == 12 { let branch = 7; emit branch; } else { emit 0; }
    emit branch;
  `;
  assertBackendsAgree(source, [false, 12, 7, 7]);

  assertBackendsAgree(
    "let go = true; while go { let once = 9; set go = false; } emit once;",
    [9],
  );

  assertBackendsAgree("if false { emit 1; } emit 2;", [2]);
});

test("interpreter and VM produce matching runtime error codes and messages", () => {
  const cases = [
    ["emit absent;", "UNDEFINED_VARIABLE"],
    ["set absent = 1;", "UNDEFINED_VARIABLE"],
    ["let x = 1; let x = 2;", "DUPLICATE_VARIABLE"],
    ["emit true + 1;", "TYPE_ERROR"],
    ["emit true < false;", "TYPE_ERROR"],
    ["emit !1;", "TYPE_ERROR"],
    ["if 1 { emit 1; } else { emit 2; }", "TYPE_ERROR"],
    ["while 1 { emit 1; }", "TYPE_ERROR"],
    ["emit 5 / 0;", "DIVISION_BY_ZERO"],
  ];

  for (const [source, code] of cases) {
    const treeError = captureError(() => evaluate(source));
    const vmError = captureError(() => execute(compile(source)));
    assert.ok(treeError instanceof PebbleRuntimeError, source);
    assert.ok(treeError instanceof RuntimeError, source);
    assert.ok(vmError instanceof PebbleRuntimeError, source);
    assert.equal(treeError.code, code, source);
    assert.equal(vmError.code, code, source);
    assert.equal(vmError.message, treeError.message, source);
  }
});

test("the runtime numeric domain rejects overflow before storage, emission, or equality", () => {
  const huge = `1${"0".repeat(308)}`;
  for (const source of [
    `emit ${huge} * 10;`,
    `let value = ${huge} * 10; emit value;`,
    `emit (${huge} * 10) == 0;`,
  ]) {
    const treeError = captureError(() => evaluate(source));
    const vmError = captureError(() => execute(compile(source)));
    assert.equal(treeError.code, "NON_FINITE_NUMBER", source);
    assert.equal(vmError.code, "NON_FINITE_NUMBER", source);
    assert.equal(vmError.message, treeError.message, source);
  }

  const nonFiniteAst = {
    type: "Program",
    body: [{
      type: "EmitStatement",
      expression: {
        type: "BinaryExpression",
        operator: "-",
        left: { type: "NumberLiteral", value: Infinity },
        right: { type: "NumberLiteral", value: Infinity },
      },
    }],
  };
  assert.equal(captureError(() => evaluate(nonFiniteAst)).code, "NON_FINITE_NUMBER");
  assert.ok(captureError(() => compile(nonFiniteAst)) instanceof CompileError);
});

test("initializer and assignment expressions run before binding checks", () => {
  for (const source of [
    "let x = 1; let x = missing;",
    "set missing = also_missing;",
  ]) {
    const tree = captureError(() => evaluate(source));
    const vm = captureError(() => execute(compile(source)));
    assert.equal(tree.code, "UNDEFINED_VARIABLE");
    assert.equal(vm.code, "UNDEFINED_VARIABLE");
    assert.equal(tree.message, vm.message);
  }
});

test("compiler emits deterministic constants and stack instructions", () => {
  const source = "let x = 2; if x > 1 { emit x; } else { emit 0; }";
  const expected = {
    format: "pebble-bytecode",
    version: 1,
    constants: [2, 1, 0],
    instructions: [
      { op: "CONSTANT", arg: 0 },
      { op: "DEFINE", arg: "x" },
      { op: "LOAD", arg: "x" },
      { op: "CONSTANT", arg: 1 },
      { op: "GREATER" },
      { op: "JUMP_IF_FALSE", arg: 9 },
      { op: "LOAD", arg: "x" },
      { op: "EMIT" },
      { op: "JUMP", arg: 11 },
      { op: "CONSTANT", arg: 2 },
      { op: "EMIT" },
      { op: "HALT" },
    ],
  };
  assert.deepEqual(compile(source), expected);
  assert.deepEqual(compile(source), compile(parse(source)));
  assert.notStrictEqual(compile(source), compile(source));
  assert.equal(DEFAULT_MAX_STEPS, 10_000);
  assert.ok(Object.isFrozen(OpCode));
  assert.deepEqual(Object.values(OpCode), [
    "CONSTANT", "LOAD", "DEFINE", "STORE", "EMIT", "NEGATE", "NOT", "ADD", "SUBTRACT",
    "MULTIPLY", "DIVIDE", "EQUAL", "NOT_EQUAL", "LESS", "LESS_EQUAL", "GREATER",
    "GREATER_EQUAL", "JUMP_IF_FALSE", "JUMP", "HALT",
  ]);
});

test("compile rejects malformed externally supplied ASTs", () => {
  const badOperator = {
    type: "Program",
    body: [{
      type: "EmitStatement",
      expression: {
        type: "BinaryExpression",
        operator: "constructor",
        left: { type: "NumberLiteral", value: 1 },
        right: { type: "NumberLiteral", value: 2 },
      },
    }],
  };
  const error = captureError(() => compile(badOperator));
  assert.ok(error instanceof CompileError);
  assert.equal(error.code, "INVALID_AST");
});

test("run defaults to VM and supports an explicit tree backend", () => {
  const source = "let value = 40 + 2; emit value;";
  const expected = [42];
  assert.deepEqual(run(source), expected);
  assert.deepEqual(run(source, { backend: "vm", maxSteps: 100 }), expected);
  assert.deepEqual(run(source, { backend: "tree", maxSteps: 100 }), expected);

  for (const options of [
    { backend: "jit" },
    { backend: null },
    { backend: "vm", maxSteps: -1 },
    { backend: "vm", maxSteps: null },
    { backend: "vm", maxSteps: 1.5 },
    { extra: true },
    null,
  ]) {
    const error = captureError(() => run(source, options));
    assert.ok(error instanceof PebbleRuntimeError);
    assert.equal(error.code, "INVALID_OPTIONS");
  }
});

test("VM and tree walker enforce explicit step limits", () => {
  const infinite = "while true { }";
  for (const action of [
    () => execute(compile(infinite), { maxSteps: 8 }),
    () => run(infinite, { backend: "vm", maxSteps: 8 }),
    () => run(infinite, { backend: "tree", maxSteps: 8 }),
  ]) {
    const error = captureError(action);
    assert.ok(error instanceof StepLimitError);
    assert.ok(error instanceof PebbleStepLimitError);
    assert.ok(error instanceof PebbleRuntimeError);
    assert.equal(error.code, "STEP_LIMIT_EXCEEDED");
  }
  assert.deepEqual(execute(compile(""), { maxSteps: 1 }), []);

  for (const maxSteps of [null, 0, -1, 1.5, Infinity, Number.MAX_SAFE_INTEGER + 1]) {
    const error = captureError(() => execute(compile(""), { maxSteps }));
    assert.equal(error.code, "INVALID_OPTIONS");
  }
});

test("step limits have documented backend-specific exact boundaries", () => {
  const source = "emit 1;";
  assert.deepEqual(evaluate(source, { maxSteps: 2 }), [1]);
  const exhausted = captureError(() => execute(compile(source), { maxSteps: 2 }));
  assert.ok(exhausted instanceof PebbleStepLimitError);
  assert.equal(exhausted.code, "STEP_LIMIT_EXCEEDED");
  assert.deepEqual(execute(compile(source), { maxSteps: 3 }), [1]);
});

test("VM rejects structurally malformed bytecode before execution", () => {
  const malformed = [
    null,
    {},
    { ...bytecode([], [{ op: "HALT" }]), extra: true },
    bytecode([], []),
    bytecode([], [{ op: "NOPE" }, { op: "HALT" }]),
    bytecode([], [{ op: "CONSTANT", arg: 0 }, { op: "HALT" }]),
    bytecode(["not-a-value"], [{ op: "HALT" }]),
    bytecode([Infinity], [{ op: "HALT" }]),
    bytecode([NaN], [{ op: "HALT" }]),
    bytecode([], [{ op: "JUMP", arg: 99 }, { op: "HALT" }]),
    bytecode([], [{ op: "LOAD", arg: "not valid" }, { op: "HALT" }]),
    bytecode([], [{ op: "EMIT", extra: 1 }, { op: "HALT" }]),
    bytecode([], [{ op: "HALT" }, { op: "HALT" }]),
    bytecode([], [{ op: "JUMP", arg: 0 }]),
  ];

  for (const candidate of malformed) {
    const error = captureError(() => execute(candidate));
    assert.ok(error instanceof BytecodeError);
    assert.ok(error instanceof PebbleRuntimeError);
    assert.equal(error.code, "INVALID_BYTECODE");
  }
});

test("VM detects malformed stack behavior and still reports source type failures separately", () => {
  const underflow = captureError(() => execute(bytecode([], [{ op: "EMIT" }, { op: "HALT" }])));
  assert.ok(underflow instanceof BytecodeError);
  assert.equal(underflow.code, "INVALID_BYTECODE");

  const leftover = captureError(() => execute(bytecode(
    [1],
    [{ op: "CONSTANT", arg: 0 }, { op: "HALT" }],
  )));
  assert.ok(leftover instanceof BytecodeError);
  assert.equal(leftover.code, "INVALID_BYTECODE");

  const wrongTypes = captureError(() => execute(bytecode(
    [true, 1],
    [
      { op: "CONSTANT", arg: 0 },
      { op: "CONSTANT", arg: 1 },
      { op: "ADD" },
      { op: "EMIT" },
      { op: "HALT" },
    ],
  )));
  assert.ok(wrongTypes instanceof PebbleRuntimeError);
  assert.ok(!(wrongTypes instanceof BytecodeError));
  assert.equal(wrongTypes.code, "TYPE_ERROR");
});
