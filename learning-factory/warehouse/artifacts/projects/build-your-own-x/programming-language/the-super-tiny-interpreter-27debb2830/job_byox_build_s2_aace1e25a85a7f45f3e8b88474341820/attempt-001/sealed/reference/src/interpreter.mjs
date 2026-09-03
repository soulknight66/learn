import { MicaRuntimeError } from "./diagnostics.mjs";
import { applyBinary, applyUnary, formatValue, isTruthy } from "./runtime.mjs";

class Environment {
  constructor() {
    this.scopes = [new Map()];
  }

  enter() {
    this.scopes.push(new Map());
  }

  exit() {
    if (this.scopes.length === 1) throw new Error("cannot exit global scope");
    this.scopes.pop();
  }

  define(name, value, span) {
    const scope = this.scopes.at(-1);
    if (scope.has(name)) {
      throw new MicaRuntimeError("E_DUPLICATE_BINDING", `duplicate binding '${name}'`, span);
    }
    scope.set(name, value);
  }

  get(name, span) {
    for (let index = this.scopes.length - 1; index >= 0; index -= 1) {
      if (this.scopes[index].has(name)) return this.scopes[index].get(name);
    }
    throw new MicaRuntimeError("E_UNDEFINED_NAME", `undefined name '${name}'`, span);
  }

  assign(name, value, span) {
    for (let index = this.scopes.length - 1; index >= 0; index -= 1) {
      if (this.scopes[index].has(name)) {
        this.scopes[index].set(name, value);
        return value;
      }
    }
    throw new MicaRuntimeError("E_UNDEFINED_NAME", `undefined name '${name}'`, span);
  }
}

export function interpret(program) {
  if (program?.type !== "Program" || !Array.isArray(program.body)) {
    throw new TypeError("interpret expects a Program AST");
  }

  const environment = new Environment();
  const output = [];

  const evaluateExpression = (node) => {
    switch (node?.type) {
      case "Literal": return node.value;
      case "Identifier": return environment.get(node.name, node.span);
      case "UnaryExpression":
        return applyUnary(node.operator, evaluateExpression(node.argument), node.span);
      case "BinaryExpression": {
        const left = evaluateExpression(node.left);
        const right = evaluateExpression(node.right);
        return applyBinary(node.operator, left, right, node.span);
      }
      case "AssignmentExpression": {
        const value = evaluateExpression(node.value);
        return environment.assign(node.name, value, node.span);
      }
      default:
        throw new TypeError(`unknown expression node '${node?.type}'`);
    }
  };

  const evaluateSequence = (statements) => {
    let value = null;
    for (const statement of statements) value = evaluateStatement(statement);
    return value;
  };

  const evaluateBlock = (node) => {
    environment.enter();
    try {
      return evaluateSequence(node.body);
    } finally {
      environment.exit();
    }
  };

  function evaluateStatement(node) {
    switch (node?.type) {
      case "LetStatement": {
        const value = evaluateExpression(node.initializer);
        environment.define(node.name.name, value, node.name.span);
        return null;
      }
      case "PrintStatement":
        output.push(formatValue(evaluateExpression(node.expression)));
        return null;
      case "ExpressionStatement": return evaluateExpression(node.expression);
      case "BlockStatement": return evaluateBlock(node);
      case "IfStatement":
        if (isTruthy(evaluateExpression(node.test))) return evaluateBlock(node.consequent);
        return node.alternate === null ? null : evaluateBlock(node.alternate);
      default:
        throw new TypeError(`unknown statement node '${node?.type}'`);
    }
  }

  return { value: evaluateSequence(program.body), output };
}
