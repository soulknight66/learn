'use strict';

const { parse, analyze } = require('../reference/compiler.js');

const BUILTIN_RUNNERS = Object.freeze({
  abs: (args) => Math.abs(args[0]),
  sqrt: (args) => Math.sqrt(args[0]),
  pow: (args) => Math.pow(args[0], args[1]),
  min: (args) => Math.min(...args),
  max: (args) => Math.max(...args),
  len: (args) => {
    if (typeof args[0] !== 'string') {
      throw new TypeError('len expects a string');
    }
    return [...args[0]].length;
  },
});

function compileBytecode(sourceOrAst) {
  const ast = typeof sourceOrAst === 'string' ? parse(sourceOrAst) : sourceOrAst;
  const analysis = analyze(ast);
  const instructions = [];

  function emit(op, argument) {
    const instruction = argument === undefined ? { op } : { op, argument };
    instructions.push(instruction);
    return instructions.length - 1;
  }

  function expression(node) {
    switch (node.type) {
      case 'Literal':
        emit('PUSH', node.value);
        return;
      case 'Identifier':
        emit('LOAD', analysis.referenceIds.get(node));
        return;
      case 'UnaryExpression':
        expression(node.argument);
        emit('UNARY', node.operator);
        return;
      case 'BinaryExpression': {
        expression(node.left);
        if (node.operator === '&&' || node.operator === '||') {
          emit('DUP');
          const jump = emit(node.operator === '&&' ? 'JUMP_IF_FALSE' : 'JUMP_IF_TRUE', null);
          emit('POP');
          expression(node.right);
          instructions[jump].argument = instructions.length;
          return;
        }
        expression(node.right);
        emit('BINARY', node.operator);
        return;
      }
      case 'CallExpression':
        for (const argument of node.arguments) {
          expression(argument);
        }
        emit('CALL', { name: node.callee.name, count: node.arguments.length });
        return;
      default:
        throw new TypeError(`unknown expression node type: ${node.type}`);
    }
  }

  for (const statement of ast.body) {
    if (statement.type === 'LetStatement') {
      expression(statement.initializer);
      emit('STORE', analysis.declarationIds.get(statement));
    } else if (statement.type === 'EmitStatement') {
      expression(statement.expression);
      emit('EMIT');
    } else {
      throw new TypeError(`unknown statement node type: ${statement.type}`);
    }
  }
  emit('HALT');
  return instructions;
}

function runBytecode(instructions, options = {}) {
  if (!Array.isArray(instructions)) {
    throw new TypeError('instructions must be an array');
  }
  const maxSteps = options.maxSteps === undefined ? 100000 : options.maxSteps;
  if (!Number.isInteger(maxSteps) || maxSteps < 1) {
    throw new RangeError('maxSteps must be a positive integer');
  }

  const stack = [];
  const environment = new Map();
  const output = [];
  let pc = 0;
  let steps = 0;

  function pop() {
    if (stack.length === 0) {
      throw new Error('invalid bytecode: stack underflow');
    }
    return stack.pop();
  }

  function binary(operator, left, right) {
    switch (operator) {
      case '+': return left + right;
      case '-': return left - right;
      case '*': return left * right;
      case '/': return left / right;
      case '%': return left % right;
      case '<': return left < right;
      case '<=': return left <= right;
      case '>': return left > right;
      case '>=': return left >= right;
      case '==': return left === right;
      case '!=': return left !== right;
      default: throw new Error(`invalid bytecode binary operator: ${operator}`);
    }
  }

  while (pc < instructions.length) {
    steps += 1;
    if (steps > maxSteps) {
      throw new Error(`bytecode step limit exceeded: ${maxSteps}`);
    }
    const instruction = instructions[pc];
    pc += 1;
    if (!instruction || typeof instruction.op !== 'string') {
      throw new Error(`invalid bytecode instruction at ${pc - 1}`);
    }

    switch (instruction.op) {
      case 'PUSH':
        stack.push(instruction.argument);
        break;
      case 'LOAD':
        if (!environment.has(instruction.argument)) {
          throw new Error(`invalid bytecode: unknown binding ${instruction.argument}`);
        }
        stack.push(environment.get(instruction.argument));
        break;
      case 'STORE':
        environment.set(instruction.argument, pop());
        break;
      case 'DUP': {
        const value = pop();
        stack.push(value, value);
        break;
      }
      case 'POP':
        pop();
        break;
      case 'UNARY': {
        const value = pop();
        if (instruction.argument === '!') {
          stack.push(!value);
        } else if (instruction.argument === '-') {
          stack.push(-value);
        } else {
          throw new Error(`invalid bytecode unary operator: ${instruction.argument}`);
        }
        break;
      }
      case 'BINARY': {
        const right = pop();
        const left = pop();
        stack.push(binary(instruction.argument, left, right));
        break;
      }
      case 'JUMP_IF_FALSE':
      case 'JUMP_IF_TRUE': {
        const condition = pop();
        const shouldJump = instruction.op === 'JUMP_IF_FALSE' ? !condition : Boolean(condition);
        if (shouldJump) {
          const target = instruction.argument;
          if (!Number.isInteger(target) || target < 0 || target >= instructions.length) {
            throw new Error(`invalid bytecode jump target: ${String(target)}`);
          }
          pc = target;
        }
        break;
      }
      case 'CALL': {
        const { name, count } = instruction.argument || {};
        if (!Object.prototype.hasOwnProperty.call(BUILTIN_RUNNERS, name)
            || !Number.isInteger(count) || count < 0 || count > stack.length) {
          throw new Error('invalid bytecode call');
        }
        const args = stack.splice(stack.length - count, count);
        stack.push(BUILTIN_RUNNERS[name](args));
        break;
      }
      case 'EMIT':
        output.push(pop());
        break;
      case 'HALT':
        if (stack.length !== 0) {
          throw new Error(`invalid bytecode: ${stack.length} value(s) left on stack`);
        }
        return output;
      default:
        throw new Error(`invalid bytecode opcode: ${instruction.op}`);
    }
  }
  throw new Error('invalid bytecode: missing HALT');
}

module.exports = { compileBytecode, runBytecode };
