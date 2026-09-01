import { Lexer } from "./lexer.js";
import { Parser } from "./parser.js";
import { Evaluator } from "./evaluator.js";
import { Compiler } from "./compiler.js";
import { VirtualMachine } from "./vm.js";
import { PebbleRuntimeError } from "./errors.js";

export { TokenType } from "./tokens.js";
export { OpCode } from "./opcodes.js";
export {
  PebbleSyntaxError,
  PebbleRuntimeError,
  PebbleStepLimitError
} from "./errors.js";

export function tokenize(source) {
  return new Lexer(source).tokenize();
}

export function parse(sourceOrTokens) {
  const tokens = typeof sourceOrTokens === "string"
    ? tokenize(sourceOrTokens)
    : sourceOrTokens;
  return new Parser(tokens).parse();
}

export function evaluate(ast, options = {}) {
  return new Evaluator(normalizeExecutionOptions(options)).evaluate(ast);
}

export function compile(ast) {
  return new Compiler().compile(ast);
}

export function execute(bytecode, options = {}) {
  return new VirtualMachine(normalizeExecutionOptions(options)).execute(bytecode);
}

export function run(source, options = {}) {
  if (options === null || typeof options !== "object" || Array.isArray(options)) {
    throw new PebbleRuntimeError("Pebble run options must be an object", {
      code: "INVALID_OPTIONS"
    });
  }

  for (const key of Reflect.ownKeys(options)) {
    if (key !== "backend" && key !== "maxSteps") {
      throw new PebbleRuntimeError(`Unknown Pebble run option: ${String(key)}`, {
        code: "INVALID_OPTIONS"
      });
    }
  }

  const backend = options.backend === undefined ? "vm" : options.backend;
  if (backend !== "tree" && backend !== "vm") {
    throw new PebbleRuntimeError(`Unknown Pebble backend: ${String(backend)}`, {
      code: "INVALID_OPTIONS"
    });
  }

  const executionOptions = normalizeExecutionOptions(
    options.maxSteps === undefined ? {} : { maxSteps: options.maxSteps }
  );
  const ast = parse(source);

  if (backend === "tree") {
    return new Evaluator(executionOptions).evaluate(ast);
  }

  return new VirtualMachine(executionOptions).execute(new Compiler().compile(ast));
}

function normalizeExecutionOptions(options) {
  if (options === null || typeof options !== "object" || Array.isArray(options)) {
    throw new PebbleRuntimeError("Pebble execution options must be an object", {
      code: "INVALID_OPTIONS"
    });
  }

  for (const key of Reflect.ownKeys(options)) {
    if (key !== "maxSteps") {
      throw new PebbleRuntimeError(`Unknown Pebble execution option: ${String(key)}`, {
        code: "INVALID_OPTIONS"
      });
    }
  }

  const maxSteps = options.maxSteps === undefined ? 10_000 : options.maxSteps;
  if (!Number.isSafeInteger(maxSteps) || maxSteps <= 0) {
    throw new PebbleRuntimeError("maxSteps must be a positive safe integer", {
      code: "INVALID_OPTIONS"
    });
  }

  return { maxSteps };
}
