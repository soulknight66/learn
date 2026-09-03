const BINARY_OPS = Object.freeze({
  "+": "ADD",
  "-": "SUBTRACT",
  "*": "MULTIPLY",
  "/": "DIVIDE",
  "==": "EQUAL",
  "!=": "NOT_EQUAL",
  "<": "LESS",
  "<=": "LESS_EQUAL",
  ">": "GREATER",
  ">=": "GREATER_EQUAL",
});

const UNARY_OPS = Object.freeze({ "-": "NEGATE", "!": "NOT" });

export function compile(program) {
  if (program?.type !== "Program" || !Array.isArray(program.body)) {
    throw new TypeError("compile expects a Program AST");
  }

  const constants = [];
  const code = [];
  const emit = (op, arg = null, span = null) => {
    code.push({ op, arg, span });
    return code.length - 1;
  };
  const patch = (index, target) => {
    code[index] = { ...code[index], arg: target };
  };
  const emitConstant = (value, span) => emit("CONSTANT", constants.push(value) - 1, span);

  const compileExpression = (node) => {
    switch (node?.type) {
      case "Literal":
        emitConstant(node.value, node.span);
        return;
      case "Identifier":
        emit("LOAD", node.name, node.span);
        return;
      case "AssignmentExpression":
        compileExpression(node.value);
        emit("STORE", node.name, node.span);
        return;
      case "UnaryExpression":
        compileExpression(node.argument);
        if (!Object.hasOwn(UNARY_OPS, node.operator)) {
          throw new TypeError(`unknown unary operator '${node.operator}'`);
        }
        emit(UNARY_OPS[node.operator], null, node.span);
        return;
      case "BinaryExpression":
        compileExpression(node.left);
        compileExpression(node.right);
        if (!Object.hasOwn(BINARY_OPS, node.operator)) {
          throw new TypeError(`unknown binary operator '${node.operator}'`);
        }
        emit(BINARY_OPS[node.operator], null, node.span);
        return;
      default:
        throw new TypeError(`unknown expression node '${node?.type}'`);
    }
  };

  const compileSequence = (statements, fallbackSpan) => {
    if (statements.length === 0) {
      emitConstant(null, fallbackSpan);
      return;
    }
    statements.forEach((statement, index) => {
      compileStatement(statement);
      if (index + 1 < statements.length) emit("POP", null, statement.span);
    });
  };

  const compileBlock = (node) => {
    emit("ENTER_SCOPE", null, node.span);
    compileSequence(node.body, node.span);
    emit("EXIT_SCOPE", null, node.span);
  };

  function compileStatement(node) {
    switch (node?.type) {
      case "LetStatement":
        compileExpression(node.initializer);
        emit("DEFINE", node.name.name, node.name.span);
        emitConstant(null, node.span);
        return;
      case "PrintStatement":
        compileExpression(node.expression);
        emit("PRINT", null, node.span);
        emitConstant(null, node.span);
        return;
      case "ExpressionStatement":
        compileExpression(node.expression);
        return;
      case "BlockStatement":
        compileBlock(node);
        return;
      case "IfStatement": {
        compileExpression(node.test);
        const falseJump = emit("JUMP_IF_FALSE", -1, node.test.span);
        compileBlock(node.consequent);
        const endJump = emit("JUMP", -1, node.span);
        patch(falseJump, code.length);
        if (node.alternate === null) emitConstant(null, node.span);
        else compileBlock(node.alternate);
        patch(endJump, code.length);
        return;
      }
      default:
        throw new TypeError(`unknown statement node '${node?.type}'`);
    }
  }

  compileSequence(program.body, program.span);
  emit("HALT", null, program.span);
  return { constants, code };
}
