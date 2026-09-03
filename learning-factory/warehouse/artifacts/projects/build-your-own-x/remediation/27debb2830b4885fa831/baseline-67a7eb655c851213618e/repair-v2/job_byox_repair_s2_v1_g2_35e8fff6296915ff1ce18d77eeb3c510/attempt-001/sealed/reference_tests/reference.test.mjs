import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { compile } from "../reference/src/compiler.mjs";
import { MicaRuntimeError, MicaSyntaxError } from "../reference/src/diagnostics.mjs";
import { interpret } from "../reference/src/interpreter.mjs";
import { tokenize } from "../reference/src/lexer.mjs";
import { parse } from "../reference/src/parser.mjs";
import { execute } from "../reference/src/pipeline.mjs";
import { run } from "../reference/src/vm.mjs";

test("supplied CLI sample is valid and has backend parity", async () => {
  const source = await readFile(new URL("../../starter/example.mica", import.meta.url), "utf8");
  const expected = { value: null, output: ["12"] };
  assert.deepEqual(execute(source, { backend: "tree" }), expected);
  assert.deepEqual(execute(source, { backend: "vm" }), expected);
});

test("tokenization retains lexemes, decoded literals, and exclusive spans", () => {
  const tokens = tokenize('print "a\\tb";\n// note\nlet n = 20.25;');
  assert.deepEqual(
    tokens.map(({ type }) => type),
    ["PRINT", "STRING", "SEMICOLON", "LET", "IDENTIFIER", "EQUAL", "NUMBER", "SEMICOLON", "EOF"],
  );
  assert.equal(tokens[1].lexeme, '"a\\tb"');
  assert.equal(tokens[1].literal, "a\tb");
  assert.deepEqual(tokens[3].span.start, { offset: 22, line: 3, column: 1 });
  assert.deepEqual(tokens.at(-1).span.start, tokens.at(-1).span.end);
});

test("lexer rejects unsupported escapes and unfinished strings", () => {
  assert.throws(
    () => tokenize('"bad\\q";'),
    (error) => error instanceof MicaSyntaxError && error.code === "E_INVALID_ESCAPE",
  );
  assert.throws(
    () => tokenize('"unfinished'),
    (error) => error instanceof MicaSyntaxError && error.code === "E_UNTERMINATED_STRING",
  );
});

test("parser implements precedence, associativity, and full spans", () => {
  const tokens = tokenize("a = b = 1 + 2 * -3;");
  const snapshot = structuredClone(tokens);
  const program = parse(tokens);
  assert.deepEqual(tokens, snapshot, "parser must not mutate the token list");
  const outer = program.body[0].expression;
  assert.equal(outer.type, "AssignmentExpression");
  assert.equal(outer.name, "a");
  assert.equal(outer.value.name, "b");
  assert.equal(outer.value.value.operator, "+");
  assert.equal(outer.value.value.right.operator, "*");
  assert.equal(outer.value.value.right.right.operator, "-");
  assert.deepEqual(program.span, {
    start: { offset: 0, line: 1, column: 1 },
    end: { offset: 19, line: 1, column: 20 },
  });
});

test("parser rejects missing delimiters and grouped assignment targets", () => {
  assert.throws(
    () => parse(tokenize("print 1")),
    (error) => error instanceof MicaSyntaxError && error.code === "E_EXPECTED_TOKEN",
  );
  assert.throws(
    () => parse(tokenize("(name) = 2;")),
    (error) => error instanceof MicaSyntaxError && error.code === "E_INVALID_ASSIGNMENT",
  );
});

test("tree evaluator implements values, statements, and output", () => {
  const program = parse(tokenize('let x = 4; x = x + 3; print "x=" + "7"; x * 2;'));
  assert.deepEqual(interpret(program), { value: 14, output: ["x=7"] });
});

test("initializer sees an outer binding before shadowing it", () => {
  const source = "let x = 4; { let x = x + 1; print x; } x;";
  assert.deepEqual(execute(source), { value: 4, output: ["5"] });
});

test("if executes exactly one fresh-scope branch", () => {
  const source = 'let x = 0; if (false) { missing; } else { let x = 8; print x; x; } x;';
  assert.deepEqual(execute(source), { value: 0, output: ["8"] });
});

test("empty programs, blocks, and unchosen else branches produce nil", () => {
  assert.deepEqual(execute(""), { value: null, output: [] });
  assert.deepEqual(execute("{}"), { value: null, output: [] });
  assert.deepEqual(execute("if (true) {} else { missing; }"), { value: null, output: [] });
});

test("value rules reject mixed addition and zero division", () => {
  assert.throws(
    () => execute('1 + "1";'),
    (error) => error instanceof MicaRuntimeError && error.code === "E_TYPE",
  );
  assert.throws(
    () => execute("4 / 0;"),
    (error) => error instanceof MicaRuntimeError && error.code === "E_DIV_ZERO",
  );
  assert.deepEqual(execute("!nil == true;"), { value: true, output: [] });
});

test("compiler emits resolved jumps and a final HALT", () => {
  const chunk = compile(parse(tokenize("if (true) { 1; } else { 2; }")));
  assert.equal(chunk.code.at(-1).op, "HALT");
  const jumps = chunk.code.filter(({ op }) => op === "JUMP" || op === "JUMP_IF_FALSE");
  assert.equal(jumps.length, 2);
  for (const instruction of jumps) {
    assert.ok(Number.isInteger(instruction.arg));
    assert.ok(instruction.arg >= 0 && instruction.arg < chunk.code.length);
  }
  assert.equal(chunk.code.some(({ arg }) => arg === -1), false);
});

test("tree and VM agree across representative programs", () => {
  const programs = [
    "1 + 2 * 3;",
    'print "ok"; nil;',
    "let a = 1; let b = 2; a = b = 9; a + b;",
    "let x = 1; { let y = x + 2; x = y; } x;",
    "if (0) { 7; } else { 8; }",
    "if (!true) { 1; }",
    "3 <= 3 == true;",
  ];
  for (const source of programs) {
    assert.deepEqual(execute(source, { backend: "vm" }), execute(source, { backend: "tree" }), source);
  }
});

test("tree and VM runtime diagnostics agree by code and span", () => {
  const programs = [
    "unknown;",
    '2 - "x";',
    "8 / 0;",
    "let x = 1; let x = 2;",
    "notDefined = 3;",
  ];
  for (const source of programs) {
    const errors = ["tree", "vm"].map((backend) => {
      try {
        execute(source, { backend });
        assert.fail(`expected ${backend} to reject ${source}`);
      } catch (error) {
        return error;
      }
    });
    assert.ok(errors.every((error) => error instanceof MicaRuntimeError));
    assert.equal(errors[0].code, errors[1].code, source);
    assert.deepEqual(errors[0].span, errors[1].span, source);
  }
});

test("VM rejects malformed chunks deterministically", () => {
  const malformed = [
    null,
    { constants: [], code: [] },
    { constants: [Infinity], code: [{ op: "HALT", arg: null, span: null }] },
    { constants: [], code: [{ op: "CONSTANT", arg: 4, span: null }] },
    { constants: [], code: [{ op: "MYSTERY", arg: null, span: null }] },
    { constants: [], code: [{ op: "POP", arg: null, span: null }, { op: "HALT", arg: null, span: null }] },
  ];
  for (const chunk of malformed) {
    assert.throws(
      () => run(chunk),
      (error) => error instanceof MicaRuntimeError && error.code === "E_INVALID_BYTECODE",
    );
  }
});
