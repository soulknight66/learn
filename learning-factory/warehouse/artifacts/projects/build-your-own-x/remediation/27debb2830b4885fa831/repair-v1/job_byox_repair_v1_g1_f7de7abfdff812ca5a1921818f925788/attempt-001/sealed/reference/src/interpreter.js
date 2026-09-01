import { RuntimeError, boundedInteger } from "./errors.js";
import { binary, formatValue, isLanguageValue, isTruthy, unary } from "./semantics.js";

const MAX_STEPS = 100_000;

export function interpret(ast, options = {}) {
  const maxSteps = boundedInteger(options, "maxSteps", MAX_STEPS);
  return new Interpreter(maxSteps).run(ast);
}

class Environment {
  constructor(parent = null) {
    this.parent = parent;
    this.values = new Map();
  }

  define(name, value, loc) {
    if (this.values.has(name)) throw new RuntimeError(`Variable '${name}' is already defined`, loc);
    this.values.set(name, value);
    return value;
  }

  get(name, loc) {
    if (this.values.has(name)) return this.values.get(name);
    if (this.parent) return this.parent.get(name, loc);
    throw new RuntimeError(`Undefined variable '${name}'`, loc);
  }

  assign(name, value, loc) {
    if (this.values.has(name)) {
      this.values.set(name, value);
      return value;
    }
    if (this.parent) return this.parent.assign(name, value, loc);
    throw new RuntimeError(`Undefined variable '${name}'`, loc);
  }
}

class Interpreter {
  constructor(maxSteps) {
    this.maxSteps = maxSteps;
    this.steps = 0;
    this.output = [];
  }

  run(ast) {
    if (!ast || ast.type !== "Program" || !Array.isArray(ast.body)) {
      throw new RuntimeError("Expected a Program AST", ast?.loc);
    }
    const global = new Environment();
    let value = null;
    for (const statement of ast.body) value = this._execute(statement, global);
    return { value, output: [...this.output] };
  }

  _execute(node, environment) {
    this._tick(node?.loc);
    switch (node?.type) {
      case "LetStatement": {
        const name = requireIdentifier(node.name, node.loc);
        const value = this._evaluate(node.initializer, environment);
        return environment.define(name, value, node.name.loc);
      }
      case "PrintStatement": {
        const value = this._evaluate(node.expression, environment);
        this.output.push(formatValue(value));
        return value;
      }
      case "ExpressionStatement":
        return this._evaluate(node.expression, environment);
      case "BlockStatement":
        return this._block(node, new Environment(environment));
      case "IfStatement":
        if (isTruthy(this._evaluate(node.test, environment))) {
          return this._execute(node.consequent, environment);
        }
        return node.alternate ? this._execute(node.alternate, environment) : null;
      case "WhileStatement": {
        let value = null;
        while (isTruthy(this._evaluate(node.test, environment))) {
          value = this._execute(node.body, environment);
        }
        return value;
      }
      default:
        throw new RuntimeError(`Unknown statement node ${JSON.stringify(node?.type)}`, node?.loc);
    }
  }

  _block(node, environment) {
    if (!Array.isArray(node.body)) throw new RuntimeError("Block body must be an array", node.loc);
    let value = null;
    for (const statement of node.body) value = this._execute(statement, environment);
    return value;
  }

  _evaluate(node, environment) {
    this._tick(node?.loc);
    switch (node?.type) {
      case "Literal":
        if (!isLanguageValue(node.value)) throw new RuntimeError("Invalid literal value", node.loc);
        return node.value;
      case "Identifier":
        return environment.get(requireIdentifier(node, node.loc), node.loc);
      case "AssignmentExpression": {
        const value = this._evaluate(node.value, environment);
        return environment.assign(requireIdentifier(node.name, node.loc), value, node.name.loc);
      }
      case "UnaryExpression":
        return unary(node.operator, this._evaluate(node.argument, environment), node.loc);
      case "BinaryExpression": {
        return this._binaryChain(node, environment);
      }
      case "LogicalExpression": {
        return this._logicalChain(node, environment);
      }
      default:
        throw new RuntimeError(`Unknown expression node ${JSON.stringify(node?.type)}`, node?.loc);
    }
  }

  _binaryChain(root, environment) {
    const chain = [];
    let expression = root;
    let first = true;
    while (expression && expression.type === "BinaryExpression") {
      if (first) first = false;
      else this._tick(expression.loc);
      chain.push(expression);
      expression = expression.left;
    }
    let value = this._evaluate(expression, environment);
    for (let index = chain.length - 1; index >= 0; index -= 1) {
      const node = chain[index];
      value = binary(node.operator, value, this._evaluate(node.right, environment), node.loc);
    }
    return value;
  }

  _logicalChain(root, environment) {
    const chain = [];
    let expression = root;
    let first = true;
    while (expression && expression.type === "LogicalExpression") {
      if (first) first = false;
      else this._tick(expression.loc);
      chain.push(expression);
      expression = expression.left;
    }
    let value = this._evaluate(expression, environment);
    for (let index = chain.length - 1; index >= 0; index -= 1) {
      const node = chain[index];
      if (node.operator === "or") {
        if (!isTruthy(value)) value = this._evaluate(node.right, environment);
      } else if (node.operator === "and") {
        if (isTruthy(value)) value = this._evaluate(node.right, environment);
      } else {
        throw new RuntimeError(`Unknown logical operator ${JSON.stringify(node.operator)}`, node.loc);
      }
    }
    return value;
  }

  _tick(loc) {
    this.steps += 1;
    if (this.steps > this.maxSteps) {
      throw new RuntimeError(`Execution step limit ${this.maxSteps} exceeded`, loc);
    }
  }
}

function requireIdentifier(node, loc) {
  if (!node || node.type !== "Identifier" || typeof node.name !== "string" ||
      !/^[A-Za-z_][A-Za-z0-9_]*$/.test(node.name)) {
    throw new RuntimeError("Expected an identifier", loc);
  }
  return node.name;
}
