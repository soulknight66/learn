import { tokenize } from "./lexer.js";
import { parse } from "./parser.js";
import { interpret } from "./interpreter.js";
import { compile } from "./compiler.js";
import { runBytecode } from "./vm.js";

export { tokenize, parse, interpret, compile, runBytecode };
export * from "./errors.js";
export { TokenType } from "./tokens.js";

export function execute(source, options = {}) {
  const engine = options.engine ?? "tree";
  if (engine !== "tree" && engine !== "vm") {
    throw new TypeError(`Unknown engine: ${String(engine)}`);
  }
  const tokens = tokenize(source, options);
  const ast = parse(tokens, options);
  return engine === "tree"
    ? interpret(ast, options)
    : runBytecode(compile(ast, options), options);
}
