import { compile } from "./compiler.mjs";
import { interpret } from "./interpreter.mjs";
import { tokenize } from "./lexer.mjs";
import { parse } from "./parser.mjs";
import { run } from "./vm.mjs";

export function execute(source, { backend = "tree" } = {}) {
  const program = parse(tokenize(source));
  if (backend === "tree") return interpret(program);
  if (backend === "vm") return run(compile(program));
  throw new TypeError(`unknown backend: ${backend}`);
}
