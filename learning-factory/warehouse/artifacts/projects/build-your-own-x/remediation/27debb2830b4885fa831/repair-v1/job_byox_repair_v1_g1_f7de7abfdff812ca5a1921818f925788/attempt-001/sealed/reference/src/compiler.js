import { CompileError, boundedInteger } from "./errors.js";
import { isLanguageValue } from "./semantics.js";

const MAX_INSTRUCTIONS = 500_000;
const MAX_CONSTANTS = 200_000;
const MAX_COMPILE_DEPTH = 1_000;

export function compile(ast, options = {}) {
  const limits = {
    instructions: boundedInteger(options, "maxInstructions", MAX_INSTRUCTIONS),
    constants: boundedInteger(options, "maxConstants", MAX_CONSTANTS),
    depth: boundedInteger(options, "maxCompileDepth", MAX_COMPILE_DEPTH)
  };
  return new Compiler(limits).compile(ast);
}

class Compiler {
  constructor(limits) {
    this.limits = limits;
    this.constants = [];
    this.code = [];
    this.depth = 0;
  }

  compile(ast) {
    if (!ast || ast.type !== "Program" || !Array.isArray(ast.body)) {
      throw new CompileError("Expected a Program AST", ast?.loc);
    }
    if (ast.body.length === 0) {
      this._emit("NULL", undefined, ast.loc);
    } else {
      ast.body.forEach((statement, index) => {
        this._statementGuarded(statement);
        if (index + 1 < ast.body.length) this._emit("POP", undefined, statement.loc);
      });
    }
    this._emit("HALT", undefined, ast.loc);
    return { version: 1, constants: [...this.constants], code: this.code.map((item) => ({ ...item, loc: { ...item.loc } })) };
  }

  _statementGuarded(node) { return this._guard(node?.loc, () => this._statement(node)); }
  _expressionGuarded(node) { return this._guard(node?.loc, () => this._expression(node)); }

  _statement(node) {
    switch (node?.type) {
      case "LetStatement":
        this._expressionGuarded(node.initializer);
        this._emit("DEFINE", identifierName(node.name, node.loc), node.name.loc);
        return;
      case "PrintStatement":
        this._expressionGuarded(node.expression);
        this._emit("PRINT", undefined, node.loc);
        return;
      case "ExpressionStatement":
        this._expressionGuarded(node.expression);
        return;
      case "BlockStatement":
        this._emit("ENTER_SCOPE", undefined, node.loc);
        if (!Array.isArray(node.body)) throw new CompileError("Block body must be an array", node.loc);
        if (node.body.length === 0) {
          this._emit("NULL", undefined, node.loc);
        } else {
          node.body.forEach((statement, index) => {
            this._statementGuarded(statement);
            if (index + 1 < node.body.length) this._emit("POP", undefined, statement.loc);
          });
        }
        this._emit("EXIT_SCOPE", undefined, node.loc);
        return;
      case "IfStatement": {
        this._expressionGuarded(node.test);
        const falseJump = this._jump("JUMP_IF_FALSE", node.loc);
        this._emit("POP", undefined, node.loc);
        this._statementGuarded(node.consequent);
        const endJump = this._jump("JUMP", node.loc);
        this._patch(falseJump);
        this._emit("POP", undefined, node.loc);
        if (node.alternate === null || node.alternate === undefined) {
          this._emit("NULL", undefined, node.loc);
        } else {
          this._statementGuarded(node.alternate);
        }
        this._patch(endJump);
        return;
      }
      case "WhileStatement": {
        this._emit("NULL", undefined, node.loc);
        const loopStart = this.code.length;
        this._expressionGuarded(node.test);
        const exitJump = this._jump("JUMP_IF_FALSE", node.loc);
        this._emit("POP", undefined, node.loc);
        this._emit("POP", undefined, node.loc);
        this._statementGuarded(node.body);
        this._emit("JUMP", loopStart, node.loc);
        this._patch(exitJump);
        this._emit("POP", undefined, node.loc);
        return;
      }
      default:
        throw new CompileError(`Unknown statement node ${JSON.stringify(node?.type)}`, node?.loc);
    }
  }

  _expression(node) {
    switch (node?.type) {
      case "Literal":
        if (!isLanguageValue(node.value)) throw new CompileError("Invalid literal value", node.loc);
        if (node.value === null) this._emit("NULL", undefined, node.loc);
        else if (node.value === true) this._emit("TRUE", undefined, node.loc);
        else if (node.value === false) this._emit("FALSE", undefined, node.loc);
        else this._emit("CONSTANT", this._constant(node.value, node.loc), node.loc);
        return;
      case "Identifier":
        this._emit("GET", identifierName(node, node.loc), node.loc);
        return;
      case "AssignmentExpression":
        this._expressionGuarded(node.value);
        this._emit("SET", identifierName(node.name, node.loc), node.loc);
        return;
      case "UnaryExpression":
        this._expressionGuarded(node.argument);
        if (node.operator === "-") this._emit("NEGATE", undefined, node.loc);
        else if (node.operator === "!") this._emit("NOT", undefined, node.loc);
        else throw new CompileError(`Unknown unary operator ${JSON.stringify(node.operator)}`, node.loc);
        return;
      case "BinaryExpression": {
        this._binaryChain(node);
        return;
      }
      case "LogicalExpression": {
        this._logicalChain(node);
        return;
      }
      default:
        throw new CompileError(`Unknown expression node ${JSON.stringify(node?.type)}`, node?.loc);
    }
  }

  _binaryChain(root) {
    const chain = [];
    let expression = root;
    while (expression && expression.type === "BinaryExpression") {
      if (chain.length >= this.limits.instructions) {
        throw new CompileError(`Instruction count exceeds ${this.limits.instructions}`, expression.loc);
      }
      chain.push(expression);
      expression = expression.left;
    }
    this._expressionGuarded(expression);
    for (let index = chain.length - 1; index >= 0; index -= 1) {
      const node = chain[index];
      this._expressionGuarded(node.right);
      const opcode = {
        "+": "ADD", "-": "SUBTRACT", "*": "MULTIPLY", "/": "DIVIDE",
        "==": "EQUAL", "!=": "NOT_EQUAL", ">": "GREATER", ">=": "GREATER_EQUAL",
        "<": "LESS", "<=": "LESS_EQUAL"
      }[node.operator];
      if (!opcode) {
        throw new CompileError(`Unknown binary operator ${JSON.stringify(node.operator)}`, node.loc);
      }
      this._emit(opcode, undefined, node.loc);
    }
  }

  _logicalChain(root) {
    const chain = [];
    let expression = root;
    while (expression && expression.type === "LogicalExpression") {
      if (chain.length >= this.limits.instructions) {
        throw new CompileError(`Instruction count exceeds ${this.limits.instructions}`, expression.loc);
      }
      chain.push(expression);
      expression = expression.left;
    }
    this._expressionGuarded(expression);
    for (let index = chain.length - 1; index >= 0; index -= 1) {
      const node = chain[index];
      if (node.operator === "or") {
        const rightJump = this._jump("JUMP_IF_FALSE", node.loc);
        const endJump = this._jump("JUMP", node.loc);
        this._patch(rightJump);
        this._emit("POP", undefined, node.loc);
        this._expressionGuarded(node.right);
        this._patch(endJump);
      } else if (node.operator === "and") {
        const endJump = this._jump("JUMP_IF_FALSE", node.loc);
        this._emit("POP", undefined, node.loc);
        this._expressionGuarded(node.right);
        this._patch(endJump);
      } else {
        throw new CompileError(`Unknown logical operator ${JSON.stringify(node.operator)}`, node.loc);
      }
    }
  }

  _constant(value, loc) {
    if (this.constants.length >= this.limits.constants) {
      throw new CompileError(`Constant count exceeds ${this.limits.constants}`, loc);
    }
    this.constants.push(value);
    return this.constants.length - 1;
  }

  _emit(op, arg, loc) {
    if (this.code.length >= this.limits.instructions) {
      throw new CompileError(`Instruction count exceeds ${this.limits.instructions}`, loc);
    }
    const instruction = { op };
    if (arg !== undefined) instruction.arg = arg;
    instruction.loc = normalizedLocation(loc);
    this.code.push(instruction);
    return this.code.length - 1;
  }

  _jump(op, loc) { return this._emit(op, -1, loc); }
  _patch(index) { this.code[index].arg = this.code.length; }

  _guard(loc, callback) {
    this.depth += 1;
    if (this.depth > this.limits.depth) {
      this.depth -= 1;
      throw new CompileError(`Compile depth exceeds ${this.limits.depth}`, loc);
    }
    try { return callback(); } finally { this.depth -= 1; }
  }
}

function identifierName(node, loc) {
  if (!node || node.type !== "Identifier" || typeof node.name !== "string" ||
      !/^[A-Za-z_][A-Za-z0-9_]*$/.test(node.name)) {
    throw new CompileError("Expected an identifier", loc);
  }
  return node.name;
}

function normalizedLocation(loc) {
  if (!Number.isInteger(loc?.line) || loc.line < 1 || !Number.isInteger(loc?.column) || loc.column < 1) {
    throw new CompileError("AST node has an invalid location", loc);
  }
  return { line: loc.line, column: loc.column };
}
