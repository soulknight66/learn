export {
  PebbleError,
  LexerError,
  ParseError,
  PebbleSyntaxError,
  PebbleRuntimeError,
  RuntimeError,
  CompileError,
  BytecodeError,
  PebbleStepLimitError,
  StepLimitError,
} from "./errors.js";
export { TokenType, tokenize } from "./lexer.js";
export { parse } from "./parser.js";
export { evaluate } from "./interpreter.js";
export { BYTECODE_FORMAT, BYTECODE_VERSION, OpCode, compile } from "./compiler.js";
export { DEFAULT_MAX_STEPS, execute } from "./vm.js";

import { compile } from "./compiler.js";
import { PebbleRuntimeError } from "./errors.js";
import { evaluate } from "./interpreter.js";
import { parse } from "./parser.js";
import { execute } from "./vm.js";

/** Run through the VM by default, or select the tree-walking interpreter. */
export function run(sourceOrAst, options = {}) {
  if (options === null || typeof options !== "object" || Array.isArray(options)) {
    throw new PebbleRuntimeError("run options must be an object", "INVALID_OPTIONS");
  }
  for (const key of Reflect.ownKeys(options)) {
    if (key !== "backend" && key !== "maxSteps") {
      throw new PebbleRuntimeError(`unknown run option '${String(key)}'`, "INVALID_OPTIONS");
    }
  }
  const backend = options.backend === undefined ? "vm" : options.backend;
  const maxSteps = options.maxSteps === undefined ? 10_000 : options.maxSteps;
  if (backend !== "vm" && backend !== "tree") {
    throw new PebbleRuntimeError(`unknown backend '${String(backend)}'`, "INVALID_OPTIONS");
  }
  if (!Number.isSafeInteger(maxSteps) || maxSteps <= 0) {
    throw new PebbleRuntimeError("maxSteps must be a positive safe integer", "INVALID_OPTIONS");
  }

  const program = typeof sourceOrAst === "string" ? parse(sourceOrAst) : sourceOrAst;
  if (backend === "tree") return evaluate(program, { maxSteps });
  return execute(compile(program), { maxSteps });
}
