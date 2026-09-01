import { RuntimeError, StepLimitError } from "./errors.js";
import { parse } from "./parser.js";
import {
  applyBinary,
  applyUnary,
  readMaxSteps,
  requireBoolean,
} from "./runtime-values.js";

function asProgram(sourceOrAst) {
  const program = typeof sourceOrAst === "string" ? parse(sourceOrAst) : sourceOrAst;
  if (program === null || typeof program !== "object" || program.type !== "Program" || !Array.isArray(program.body)) {
    throw new TypeError("evaluate expects source text or a Program AST");
  }
  return program;
}

/** Interpret source text or a Program AST. */
export function evaluate(sourceOrAst, options = {}) {
  const program = asProgram(sourceOrAst);
  const maxSteps = readMaxSteps(options, 10_000);
  const variables = new Map();
  const output = [];
  let steps = 0;

  const tick = () => {
    if (steps >= maxSteps) {
      throw new StepLimitError(`step limit exceeded (${maxSteps})`);
    }
    steps += 1;
  };

  const evaluateExpression = (expression) => {
    tick();
    if (expression === null || typeof expression !== "object") {
      throw new RuntimeError("invalid expression node");
    }
    switch (expression.type) {
      case "NumberLiteral":
        if (typeof expression.value !== "number" || !Number.isFinite(expression.value)) {
          throw new RuntimeError("invalid number literal");
        }
        return expression.value;
      case "BooleanLiteral":
        if (typeof expression.value !== "boolean") throw new RuntimeError("invalid boolean literal");
        return expression.value;
      case "Identifier":
        if (!variables.has(expression.name)) {
          throw new RuntimeError(`undefined variable '${expression.name}'`, "UNDEFINED_VARIABLE");
        }
        return variables.get(expression.name);
      case "UnaryExpression":
        return applyUnary(expression.operator, evaluateExpression(expression.argument));
      case "BinaryExpression": {
        const left = evaluateExpression(expression.left);
        const right = evaluateExpression(expression.right);
        return applyBinary(expression.operator, left, right);
      }
      default:
        throw new RuntimeError(`unknown expression node '${String(expression.type)}'`);
    }
  };

  const executeBlock = (block) => {
    if (block === null || typeof block !== "object" || block.type !== "BlockStatement" || !Array.isArray(block.body)) {
      throw new RuntimeError("invalid block node");
    }
    for (const statement of block.body) executeStatement(statement);
  };

  const executeStatement = (statement) => {
    tick();
    if (statement === null || typeof statement !== "object") {
      throw new RuntimeError("invalid statement node");
    }
    switch (statement.type) {
      case "LetStatement": { // The initializer runs before duplicate-name validation.
        const value = evaluateExpression(statement.initializer);
        if (variables.has(statement.name)) {
          throw new RuntimeError(`duplicate variable '${statement.name}'`, "DUPLICATE_VARIABLE");
        }
        variables.set(statement.name, value);
        return;
      }
      case "SetStatement": { // The value runs before undefined-store validation.
        const value = evaluateExpression(statement.value);
        if (!variables.has(statement.name)) {
          throw new RuntimeError(`undefined variable '${statement.name}'`, "UNDEFINED_VARIABLE");
        }
        variables.set(statement.name, value);
        return;
      }
      case "EmitStatement":
        output.push(evaluateExpression(statement.expression));
        return;
      case "IfStatement": {
        const condition = evaluateExpression(statement.condition);
        requireBoolean(condition, "condition");
        if (condition) executeBlock(statement.consequent);
        else if (statement.alternate !== null) executeBlock(statement.alternate);
        return;
      }
      case "WhileStatement":
        while (true) {
          const condition = evaluateExpression(statement.condition);
          requireBoolean(condition, "condition");
          if (!condition) return;
          executeBlock(statement.body);
        }
      default:
        throw new RuntimeError(`unknown statement node '${String(statement.type)}'`);
    }
  };

  for (const statement of program.body) executeStatement(statement);
  return output;
}
