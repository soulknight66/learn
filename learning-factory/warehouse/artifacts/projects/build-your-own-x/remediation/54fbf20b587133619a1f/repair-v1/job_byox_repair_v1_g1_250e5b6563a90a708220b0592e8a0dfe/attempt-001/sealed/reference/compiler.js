import { CompileError } from "./errors.js";
import { parse } from "./parser.js";

export const BYTECODE_FORMAT = "pebble-bytecode";
export const BYTECODE_VERSION = 1;
export const OpCode = Object.freeze({
  CONSTANT: "CONSTANT",
  LOAD: "LOAD",
  DEFINE: "DEFINE",
  STORE: "STORE",
  EMIT: "EMIT",
  NEGATE: "NEGATE",
  NOT: "NOT",
  ADD: "ADD",
  SUBTRACT: "SUBTRACT",
  MULTIPLY: "MULTIPLY",
  DIVIDE: "DIVIDE",
  EQUAL: "EQUAL",
  NOT_EQUAL: "NOT_EQUAL",
  LESS: "LESS",
  LESS_EQUAL: "LESS_EQUAL",
  GREATER: "GREATER",
  GREATER_EQUAL: "GREATER_EQUAL",
  JUMP_IF_FALSE: "JUMP_IF_FALSE",
  JUMP: "JUMP",
  HALT: "HALT",
});

const IDENTIFIER = /^[A-Za-z_][A-Za-z0-9_]*$/;

const UNARY_OPCODE = Object.freeze({ "-": OpCode.NEGATE, "!": OpCode.NOT });
const BINARY_OPCODE = Object.freeze({
  "+": OpCode.ADD,
  "-": OpCode.SUBTRACT,
  "*": OpCode.MULTIPLY,
  "/": OpCode.DIVIDE,
  "==": OpCode.EQUAL,
  "!=": OpCode.NOT_EQUAL,
  "<": OpCode.LESS,
  "<=": OpCode.LESS_EQUAL,
  ">": OpCode.GREATER,
  ">=": OpCode.GREATER_EQUAL,
});

function asProgram(sourceOrAst) {
  const program = typeof sourceOrAst === "string" ? parse(sourceOrAst) : sourceOrAst;
  if (program === null || typeof program !== "object" || program.type !== "Program" || !Array.isArray(program.body)) {
    throw new CompileError("compile expects source text or a Program AST");
  }
  return program;
}

function requireName(name) {
  if (typeof name !== "string" || !IDENTIFIER.test(name)) {
    throw new CompileError("invalid variable name in AST");
  }
}

/** Compile source text or a Program AST to deterministic stack bytecode. */
export function compile(sourceOrAst) {
  const program = asProgram(sourceOrAst);
  const constants = [];
  const instructions = [];
  const emit = (instruction) => {
    instructions.push(instruction);
    return instructions.length - 1;
  };
  const patchArg = (index, arg) => {
    instructions[index] = { ...instructions[index], arg };
  };
  const emitConstant = (value) => {
    const arg = constants.length;
    constants.push(value);
    emit({ op: OpCode.CONSTANT, arg });
  };

  const compileExpression = (expression) => {
    if (expression === null || typeof expression !== "object") {
      throw new CompileError("invalid expression node");
    }
    switch (expression.type) {
      case "NumberLiteral":
        if (typeof expression.value !== "number" || !Number.isFinite(expression.value)) {
          throw new CompileError("invalid number literal");
        }
        emitConstant(expression.value);
        return;
      case "BooleanLiteral":
        if (typeof expression.value !== "boolean") throw new CompileError("invalid boolean literal");
        emitConstant(expression.value);
        return;
      case "Identifier":
        requireName(expression.name);
        emit({ op: OpCode.LOAD, arg: expression.name });
        return;
      case "UnaryExpression": {
        const op = Object.hasOwn(UNARY_OPCODE, expression.operator)
          ? UNARY_OPCODE[expression.operator]
          : undefined;
        if (op === undefined) throw new CompileError(`unknown unary operator '${String(expression.operator)}'`);
        compileExpression(expression.argument);
        emit({ op });
        return;
      }
      case "BinaryExpression": {
        const op = Object.hasOwn(BINARY_OPCODE, expression.operator)
          ? BINARY_OPCODE[expression.operator]
          : undefined;
        if (op === undefined) throw new CompileError(`unknown binary operator '${String(expression.operator)}'`);
        compileExpression(expression.left);
        compileExpression(expression.right);
        emit({ op });
        return;
      }
      default:
        throw new CompileError(`unknown expression node '${String(expression.type)}'`);
    }
  };

  const compileBlock = (block) => {
    if (block === null || typeof block !== "object" || block.type !== "BlockStatement" || !Array.isArray(block.body)) {
      throw new CompileError("invalid block node");
    }
    for (const statement of block.body) compileStatement(statement);
  };

  const compileStatement = (statement) => {
    if (statement === null || typeof statement !== "object") {
      throw new CompileError("invalid statement node");
    }
    switch (statement.type) {
      case "LetStatement":
        requireName(statement.name);
        compileExpression(statement.initializer);
        emit({ op: OpCode.DEFINE, arg: statement.name });
        return;
      case "SetStatement":
        requireName(statement.name);
        compileExpression(statement.value);
        emit({ op: OpCode.STORE, arg: statement.name });
        return;
      case "EmitStatement":
        compileExpression(statement.expression);
        emit({ op: OpCode.EMIT });
        return;
      case "IfStatement": { // JUMP_IF_FALSE consumes its condition.
        compileExpression(statement.condition);
        const toAlternate = emit({ op: OpCode.JUMP_IF_FALSE, arg: -1 });
        compileBlock(statement.consequent);
        if (statement.alternate === null) {
          patchArg(toAlternate, instructions.length);
        } else {
          const toEnd = emit({ op: OpCode.JUMP, arg: -1 });
          patchArg(toAlternate, instructions.length);
          compileBlock(statement.alternate);
          patchArg(toEnd, instructions.length);
        }
        return;
      }
      case "WhileStatement": {
        const loopStart = instructions.length;
        compileExpression(statement.condition);
        const toEnd = emit({ op: OpCode.JUMP_IF_FALSE, arg: -1 });
        compileBlock(statement.body);
        emit({ op: OpCode.JUMP, arg: loopStart });
        patchArg(toEnd, instructions.length);
        return;
      }
      default:
        throw new CompileError(`unknown statement node '${String(statement.type)}'`);
    }
  };

  for (const statement of program.body) compileStatement(statement);
  emit({ op: OpCode.HALT });
  return { format: BYTECODE_FORMAT, version: BYTECODE_VERSION, constants, instructions };
}
