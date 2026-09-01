#!/usr/bin/env python3
"""Emit a legacy-GJS smoke bundle derived mechanically from the reference modules."""

from __future__ import print_function

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODULES = [
    ("reference/src/errors.js", [
        "LanguageError", "LexError", "ParseError", "RuntimeError", "CompileError",
        "BytecodeError", "boundedInteger"
    ]),
    ("reference/src/tokens.js", ["TokenType", "KEYWORDS"]),
    ("reference/src/lexer.js", ["tokenize"]),
    ("reference/src/parser.js", ["parse"]),
    ("reference/src/semantics.js", [
        "isLanguageValue", "isTruthy", "formatValue", "unary", "binary"
    ]),
    ("reference/src/interpreter.js", ["interpret"]),
    ("reference/src/compiler.js", ["compile"]),
    ("reference/src/vm.js", ["runBytecode", "validateBytecode"])
]


def legacy_transform(source):
    source = re.sub(r"^import[^\n]*\n", "", source, flags=re.M)
    source = re.sub(r"\bexport\s+", "", source)
    source = re.sub(r"(?<=\d)_(?=\d)", "", source)
    source = source.replace(
        "options?.[key] ?? fallback",
        "(options == null || options[key] == null ? fallback : options[key])"
    )
    source = source.replace(
        "KEYWORDS[text] ?? T.IDENTIFIER",
        "(KEYWORDS[text] == null ? T.IDENTIFIER : KEYWORDS[text])"
    )
    source = source.replace(
        "tokens[tokens.length - 1]?.type",
        "(tokens[tokens.length - 1] == null ? undefined : tokens[tokens.length - 1].type)"
    )
    source = source.replace(
        "this._peek()?.type",
        "(this._peek() == null ? undefined : this._peek().type)"
    )
    source = re.sub(
        r"\b(location|token|ast|node|loc)\?\.(line|column|loc|type)",
        r"(\1 == null ? undefined : \1.\2)",
        source
    )
    source = source.replace("tokens.at(-1)", "tokens[tokens.length - 1]")
    source = source.replace("program.code.at(-1)", "program.code[program.code.length - 1]")
    source = source.replace("code.at(-1)", "code[code.length - 1]")
    source = source.replace("scopes.at(-1)", "scopes[scopes.length - 1]")
    source = source.replace("stack.at(-1)", "stack[stack.length - 1]")
    return source


def emit_modules():
    print("var G = this;")
    print("if (!Array.prototype.at) Array.prototype.at = function(i) { "
          "return this[i < 0 ? this.length + i : i]; };")
    for relative, names in MODULES:
        path = os.path.join(ROOT, relative)
        with open(path, "r", encoding="utf-8") as handle:
            source = legacy_transform(handle.read())
        print("(function () {")
        if relative.endswith(("lexer.js", "parser.js")):
            print("var T = G.TokenType;")
        print(source)
        for name in names:
            print("G.{0} = {0};".format(name))
        print("}).call(G);")


SMOKE = r'''
function executeSmoke(source, engine, options) {
  options = options || {};
  var ast = parse(tokenize(source, options), options);
  return engine === "tree" ? interpret(ast, options) : runBytecode(compile(ast, options), options);
}
function assertCondition(condition, message) {
  if (!condition) throw new Error(message);
}
function assertSame(source, expected) {
  var want = JSON.stringify(expected);
  var left = executeSmoke(source, "tree");
  var right = executeSmoke(source, "vm");
  assertCondition(JSON.stringify(left) === want, "tree mismatch: " + JSON.stringify(left));
  assertCondition(JSON.stringify(right) === want, "vm mismatch: " + JSON.stringify(right));
}
function expectLanguageError(source, engine, expectedName) {
  try {
    executeSmoke(source, engine);
  } catch (error) {
    assertCondition(error.name === expectedName, "wrong error: " + error.name);
    return;
  }
  throw new Error("expected " + expectedName);
}
var locationTokens = tokenize("// heading\r\nlet x=12.5;\rprint x;");
assertCondition(JSON.stringify(locationTokens.map(function (token) {
  return [token.type, token.line, token.column];
})) === JSON.stringify([
  ["LET",2,1],["IDENTIFIER",2,5],["EQUAL",2,6],["NUMBER",2,7],
  ["SEMICOLON",2,11],["PRINT",3,1],["IDENTIFIER",3,7],["SEMICOLON",3,8],["EOF",3,9]
]), "token locations differ");
assertSame("", {value: null, output: []});
assertSame("print 1 + 2 * 3;", {value: 7, output: ["7"]});
assertSame("let n=5; let p=1; while (n > 1) { p=p*n; n=n-1; } print p;",
  {value: 120, output: ["120"]});
assertSame("let x=\"outer\"; { let x=\"inner\"; x=x+\"!\"; print x; } print x;",
  {value: "outer", output: ["inner!", "outer"]});
assertSame("print false and missing; print null or \"fallback\";",
  {value: "fallback", output: ["false", "fallback"]});
assertSame("if (true) { 4; } else { missing; }", {value: 4, output: []});
["tree", "vm"].forEach(function (engine) {
  expectLanguageError("missing;", engine, "RuntimeError");
  expectLanguageError("let x=1; let x=2;", engine, "RuntimeError");
  expectLanguageError("9 / 0;", engine, "RuntimeError");
});
expectLanguageError("print \"bad\\q\";", "tree", "LexError");
expectLanguageError("(1 + 2) = 3;", "tree", "ParseError");
var malformed = {version: 1, constants: [], code: [
  {op: "PRINT", loc: {line: 1, column: 1}},
  {op: "HALT", loc: {line: 1, column: 1}}
]};
try {
  runBytecode(malformed, {});
  throw new Error("expected BytecodeError");
} catch (error) {
  assertCondition(error.name === "BytecodeError", "wrong bytecode error: " + error.name);
}
print("GJS_TRANSPILED_SMOKE_PASS");
'''


if __name__ == "__main__":
    emit_modules()
    print(SMOKE)
