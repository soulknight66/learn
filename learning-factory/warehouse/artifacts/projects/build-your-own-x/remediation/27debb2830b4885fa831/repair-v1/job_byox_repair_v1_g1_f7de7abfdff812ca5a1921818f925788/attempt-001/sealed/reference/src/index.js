import { tokenize } from "./lexer.js";
import { parse } from "./parser.js";
import { interpret } from "./interpreter.js";
import { compile } from "./compiler.js";
import { runBytecode, validateBytecode } from "./vm.js";

export { tokenize, parse, interpret, compile, runBytecode, validateBytecode };
export { TokenType } from "./tokens.js";
export * from "./errors.js";

export function execute(source, options = {}) {
  const engine = options.engine ?? "tree";
  if (engine !== "tree" && engine !== "vm") {
    throw new TypeError(`Unknown engine: ${String(engine)}`);
  }
  const ast = parse(tokenize(source, options), options);
  return engine === "tree"
    ? interpret(ast, options)
    : runBytecode(compile(ast, options), options);
}
