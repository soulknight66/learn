'use strict';

class CompilerError extends Error {
  constructor(phase, code, message, loc) {
    const where = loc || { line: 1, column: 1, offset: 0 };
    super(`${code} at ${where.line}:${where.column}: ${message}`);
    this.name = 'CompilerError';
    this.phase = phase;
    this.code = code;
    this.line = where.line;
    this.column = where.column;
    this.offset = where.offset;
  }
}

const KEYWORDS = new Set(['let', 'emit', 'true', 'false']);
const TWO_CHARACTER_OPERATORS = new Set(['==', '!=', '<=', '>=', '&&', '||']);
const ONE_CHARACTER_OPERATORS = new Set(['+', '-', '*', '/', '%', '!', '<', '>', '=']);
const PUNCTUATION = new Set(['(', ')', ',', ';']);

const BUILTINS = Object.freeze({
  abs: Object.freeze({ min: 1, max: 1, js: 'Math.abs', run: (args) => Math.abs(args[0]) }),
  sqrt: Object.freeze({ min: 1, max: 1, js: 'Math.sqrt', run: (args) => Math.sqrt(args[0]) }),
  pow: Object.freeze({ min: 2, max: 2, js: 'Math.pow', run: (args) => Math.pow(args[0], args[1]) }),
  min: Object.freeze({ min: 1, max: Infinity, js: 'Math.min', run: (args) => Math.min(...args) }),
  max: Object.freeze({ min: 1, max: Infinity, js: 'Math.max', run: (args) => Math.max(...args) }),
  len: Object.freeze({
    min: 1,
    max: 1,
    js: '__len',
    run: (args) => {
      if (typeof args[0] !== 'string') {
        throw new TypeError('len expects a string');
      }
      return [...args[0]].length;
    },
  }),
});

function hasBuiltin(name) {
  return Object.prototype.hasOwnProperty.call(BUILTINS, name);
}

function locationOf(value) {
  if (value && value.loc) {
    return value.loc;
  }
  if (value && Number.isInteger(value.line)) {
    return { line: value.line, column: value.column, offset: value.offset };
  }
  return { line: 1, column: 1, offset: 0 };
}

function copiedLocation(value) {
  const loc = locationOf(value);
  return { line: loc.line, column: loc.column, offset: loc.offset };
}

function tokenize(source) {
  if (typeof source !== 'string') {
    throw new TypeError('source must be a string');
  }

  const tokens = [];
  let offset = 0;
  let line = 1;
  let column = 1;

  function current() {
    return offset < source.length ? source[offset] : undefined;
  }

  function peek(distance = 1) {
    const target = offset + distance;
    return target < source.length ? source[target] : undefined;
  }

  function loc() {
    return { line, column, offset };
  }

  function advance() {
    const character = source[offset];
    offset += 1;
    if (character === '\n') {
      line += 1;
      column = 1;
    } else {
      column += 1;
    }
    return character;
  }

  function push(kind, value, start) {
    tokens.push({
      kind,
      value,
      line: start.line,
      column: start.column,
      offset: start.offset,
    });
  }

  function fail(code, message, start = loc()) {
    throw new CompilerError('lex', code, message, start);
  }

  function isDigit(character) {
    return character !== undefined && character >= '0' && character <= '9';
  }

  function isIdentifierStart(character) {
    return character !== undefined
      && ((character >= 'a' && character <= 'z')
        || (character >= 'A' && character <= 'Z')
        || character === '_');
  }

  function isIdentifierPart(character) {
    return isIdentifierStart(character) || isDigit(character);
  }

  while (offset < source.length) {
    const character = current();

    if (character === ' ' || character === '\t' || character === '\r' || character === '\n') {
      advance();
      continue;
    }

    if (character === '/' && peek() === '/') {
      advance();
      advance();
      while (offset < source.length && current() !== '\n') {
        advance();
      }
      continue;
    }

    const start = loc();

    if (isDigit(character)) {
      let raw = '';
      while (isDigit(current())) {
        raw += advance();
      }
      if (current() === '.' && isDigit(peek())) {
        raw += advance();
        while (isDigit(current())) {
          raw += advance();
        }
      }
      const value = Number(raw);
      if (!Number.isFinite(value)) {
        fail('LEX_INVALID_NUMBER', `number is outside the finite range: ${raw}`, start);
      }
      push('NUMBER', value, start);
      continue;
    }

    if (isIdentifierStart(character)) {
      let value = '';
      while (isIdentifierPart(current())) {
        value += advance();
      }
      push(KEYWORDS.has(value) ? 'KEYWORD' : 'IDENTIFIER', value, start);
      continue;
    }

    if (character === '"') {
      advance();
      let value = '';
      let terminated = false;
      while (offset < source.length) {
        const part = current();
        if (part === '"') {
          advance();
          terminated = true;
          break;
        }
        if (part === '\n' || part === '\r') {
          fail('LEX_UNTERMINATED_STRING', 'raw newline in string literal', start);
        }
        if (part === '\\') {
          advance();
          if (offset >= source.length) {
            fail('LEX_UNTERMINATED_STRING', 'unterminated string literal', start);
          }
          const escaped = advance();
          const escapes = {
            '\\': '\\',
            '"': '"',
            n: '\n',
            r: '\r',
            t: '\t',
          };
          if (!Object.prototype.hasOwnProperty.call(escapes, escaped)) {
            fail('LEX_UNKNOWN_ESCAPE', `unsupported escape: \\${escaped}`, start);
          }
          value += escapes[escaped];
          continue;
        }
        value += advance();
      }
      if (!terminated) {
        fail('LEX_UNTERMINATED_STRING', 'unterminated string literal', start);
      }
      push('STRING', value, start);
      continue;
    }

    const pair = character + (peek() || '');
    if (TWO_CHARACTER_OPERATORS.has(pair)) {
      advance();
      advance();
      push('OPERATOR', pair, start);
      continue;
    }

    if (ONE_CHARACTER_OPERATORS.has(character)) {
      advance();
      push('OPERATOR', character, start);
      continue;
    }

    if (PUNCTUATION.has(character)) {
      advance();
      push('PUNCTUATION', character, start);
      continue;
    }

    fail('LEX_UNEXPECTED_CHARACTER', `unexpected character ${JSON.stringify(character)}`, start);
  }

  push('EOF', null, loc());
  return tokens;
}

class Parser {
  constructor(tokens) {
    if (!Array.isArray(tokens) || tokens.length === 0 || tokens[tokens.length - 1].kind !== 'EOF') {
      throw new TypeError('tokens must be a non-empty array ending in EOF');
    }
    this.tokens = tokens;
    this.position = 0;
  }

  current() {
    return this.tokens[this.position];
  }

  check(kind, value) {
    const token = this.current();
    return token.kind === kind && (value === undefined || token.value === value);
  }

  advance() {
    const token = this.current();
    if (token.kind !== 'EOF') {
      this.position += 1;
    }
    return token;
  }

  match(kind, value) {
    if (!this.check(kind, value)) {
      return null;
    }
    return this.advance();
  }

  fail(code, message, token = this.current()) {
    throw new CompilerError('parse', code, message, locationOf(token));
  }

  consume(kind, value, code, message) {
    if (!this.check(kind, value)) {
      this.fail(code, message);
    }
    return this.advance();
  }

  parseProgram() {
    const start = this.current();
    const body = [];
    while (!this.check('EOF')) {
      body.push(this.parseStatement());
    }
    this.consume('EOF', undefined, 'PARSE_EXPECTED_EOF', 'expected end of input');
    return { type: 'Program', body, loc: copiedLocation(start) };
  }

  parseStatement() {
    if (this.check('KEYWORD', 'let')) {
      return this.parseLetStatement();
    }
    if (this.check('KEYWORD', 'emit')) {
      return this.parseEmitStatement();
    }
    this.fail('PARSE_EXPECTED_STATEMENT', 'expected a let or emit statement');
  }

  parseLetStatement() {
    const start = this.advance();
    const nameToken = this.consume(
      'IDENTIFIER',
      undefined,
      'PARSE_EXPECTED_IDENTIFIER',
      'expected a binding name after let',
    );
    this.consume('OPERATOR', '=', 'PARSE_EXPECTED_ASSIGN', 'expected = after binding name');
    const initializer = this.parseExpression();
    this.consume('PUNCTUATION', ';', 'PARSE_EXPECTED_SEMICOLON', 'expected ; after declaration');
    return {
      type: 'LetStatement',
      name: { type: 'Identifier', name: nameToken.value, loc: copiedLocation(nameToken) },
      initializer,
      loc: copiedLocation(start),
    };
  }

  parseEmitStatement() {
    const start = this.advance();
    const expression = this.parseExpression();
    this.consume('PUNCTUATION', ';', 'PARSE_EXPECTED_SEMICOLON', 'expected ; after emit value');
    return { type: 'EmitStatement', expression, loc: copiedLocation(start) };
  }

  parseExpression() {
    return this.parseOr();
  }

  parseOr() {
    return this.parseBinaryLevel(() => this.parseAnd(), ['||']);
  }

  parseAnd() {
    return this.parseBinaryLevel(() => this.parseEquality(), ['&&']);
  }

  parseEquality() {
    return this.parseBinaryLevel(() => this.parseComparison(), ['==', '!=']);
  }

  parseComparison() {
    return this.parseBinaryLevel(() => this.parseTerm(), ['<', '<=', '>', '>=']);
  }

  parseTerm() {
    return this.parseBinaryLevel(() => this.parseFactor(), ['+', '-']);
  }

  parseFactor() {
    return this.parseBinaryLevel(() => this.parseUnary(), ['*', '/', '%']);
  }

  parseBinaryLevel(parseOperand, operators) {
    let expression = parseOperand();
    while (this.check('OPERATOR') && operators.includes(this.current().value)) {
      const operator = this.advance();
      const right = parseOperand();
      expression = {
        type: 'BinaryExpression',
        operator: operator.value,
        left: expression,
        right,
        loc: copiedLocation(expression),
      };
    }
    return expression;
  }

  parseUnary() {
    if (this.check('OPERATOR', '!') || this.check('OPERATOR', '-')) {
      const operator = this.advance();
      return {
        type: 'UnaryExpression',
        operator: operator.value,
        argument: this.parseUnary(),
        loc: copiedLocation(operator),
      };
    }
    return this.parseCall();
  }

  parseCall() {
    let expression = this.parsePrimary();
    while (this.match('PUNCTUATION', '(')) {
      const args = [];
      if (!this.check('PUNCTUATION', ')')) {
        do {
          args.push(this.parseExpression());
        } while (this.match('PUNCTUATION', ','));
      }
      this.consume('PUNCTUATION', ')', 'PARSE_EXPECTED_RPAREN', 'expected ) after arguments');
      expression = {
        type: 'CallExpression',
        callee: expression,
        arguments: args,
        loc: copiedLocation(expression),
      };
    }
    return expression;
  }

  parsePrimary() {
    const token = this.current();
    if (this.match('NUMBER')) {
      return { type: 'Literal', value: token.value, loc: copiedLocation(token) };
    }
    if (this.match('STRING')) {
      return { type: 'Literal', value: token.value, loc: copiedLocation(token) };
    }
    if (this.match('KEYWORD', 'true')) {
      return { type: 'Literal', value: true, loc: copiedLocation(token) };
    }
    if (this.match('KEYWORD', 'false')) {
      return { type: 'Literal', value: false, loc: copiedLocation(token) };
    }
    if (this.match('IDENTIFIER')) {
      return { type: 'Identifier', name: token.value, loc: copiedLocation(token) };
    }
    if (this.match('PUNCTUATION', '(')) {
      const expression = this.parseExpression();
      this.consume('PUNCTUATION', ')', 'PARSE_EXPECTED_RPAREN', 'expected ) after expression');
      return expression;
    }
    this.fail('PARSE_EXPECTED_EXPRESSION', 'expected an expression');
  }
}

function parse(sourceOrTokens) {
  const tokens = typeof sourceOrTokens === 'string' ? tokenize(sourceOrTokens) : sourceOrTokens;
  return new Parser(tokens).parseProgram();
}

function analyze(ast) {
  if (!ast || ast.type !== 'Program' || !Array.isArray(ast.body)) {
    throw new TypeError('analyze expects a Program AST');
  }

  const bindings = new Map();
  const symbols = [];
  const declarationIds = new WeakMap();
  const referenceIds = new WeakMap();

  function fail(code, message, node) {
    throw new CompilerError('analyze', code, message, locationOf(node));
  }

  function visitExpression(node) {
    if (!node || typeof node.type !== 'string') {
      throw new TypeError('malformed expression node');
    }
    switch (node.type) {
      case 'Literal':
        return;
      case 'Identifier': {
        if (!bindings.has(node.name)) {
          fail('ANALYZE_UNKNOWN_IDENTIFIER', `unknown identifier ${node.name}`, node);
        }
        referenceIds.set(node, bindings.get(node.name));
        return;
      }
      case 'UnaryExpression':
        visitExpression(node.argument);
        return;
      case 'BinaryExpression':
        visitExpression(node.left);
        visitExpression(node.right);
        return;
      case 'CallExpression': {
        if (!node.callee || node.callee.type !== 'Identifier') {
          fail('ANALYZE_INVALID_CALL_TARGET', 'call target must be a bare built-in name', node.callee || node);
        }
        const name = node.callee.name;
        if (!hasBuiltin(name)) {
          if (bindings.has(name)) {
            fail('ANALYZE_NON_CALLABLE', `binding ${name} is not callable`, node.callee);
          }
          fail('ANALYZE_UNKNOWN_FUNCTION', `unknown built-in ${name}`, node.callee);
        }
        const spec = BUILTINS[name];
        const count = node.arguments.length;
        if (count < spec.min || count > spec.max) {
          const expected = spec.min === spec.max
            ? `exactly ${spec.min}`
            : `at least ${spec.min}`;
          fail(
            'ANALYZE_WRONG_ARITY',
            `${name} expects ${expected} argument${spec.min === 1 && spec.max === 1 ? '' : 's'}; got ${count}`,
            node,
          );
        }
        for (const argument of node.arguments) {
          visitExpression(argument);
        }
        return;
      }
      default:
        throw new TypeError(`unknown expression node type: ${node.type}`);
    }
  }

  for (const statement of ast.body) {
    if (statement.type === 'LetStatement') {
      visitExpression(statement.initializer);
      const name = statement.name.name;
      if (hasBuiltin(name)) {
        fail('ANALYZE_BUILTIN_BINDING', `cannot declare reserved built-in ${name}`, statement.name);
      }
      if (bindings.has(name)) {
        fail('ANALYZE_DUPLICATE_BINDING', `duplicate binding ${name}`, statement.name);
      }
      const id = symbols.length;
      bindings.set(name, id);
      symbols.push({ id, sourceName: name, generatedName: `v_${id}` });
      declarationIds.set(statement, id);
      continue;
    }
    if (statement.type === 'EmitStatement') {
      visitExpression(statement.expression);
      continue;
    }
    throw new TypeError(`unknown statement node type: ${statement.type}`);
  }

  return { ast, symbols, declarationIds, referenceIds };
}

function evaluateUnary(operator, value) {
  switch (operator) {
    case '!': return !value;
    case '-': return -value;
    default: throw new TypeError(`unknown unary operator: ${operator}`);
  }
}

function evaluateBinary(operator, left, right) {
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
    case '&&': return left && right;
    case '||': return left || right;
    default: throw new TypeError(`unknown binary operator: ${operator}`);
  }
}

function foldableValue(value) {
  return typeof value === 'string'
    || typeof value === 'boolean'
    || (typeof value === 'number' && Number.isFinite(value));
}

function optimize(ast) {
  if (!ast || ast.type !== 'Program' || !Array.isArray(ast.body)) {
    throw new TypeError('optimize expects a Program AST');
  }

  function visitExpression(node) {
    switch (node.type) {
      case 'Literal':
        return { type: 'Literal', value: node.value, loc: copiedLocation(node) };
      case 'Identifier':
        return { type: 'Identifier', name: node.name, loc: copiedLocation(node) };
      case 'UnaryExpression': {
        const argument = visitExpression(node.argument);
        if (argument.type === 'Literal') {
          const value = evaluateUnary(node.operator, argument.value);
          if (foldableValue(value)) {
            return { type: 'Literal', value, loc: copiedLocation(node) };
          }
        }
        return {
          type: 'UnaryExpression',
          operator: node.operator,
          argument,
          loc: copiedLocation(node),
        };
      }
      case 'BinaryExpression': {
        const left = visitExpression(node.left);
        const right = visitExpression(node.right);
        if (left.type === 'Literal' && right.type === 'Literal') {
          const value = evaluateBinary(node.operator, left.value, right.value);
          if (foldableValue(value)) {
            return { type: 'Literal', value, loc: copiedLocation(node) };
          }
        }
        return {
          type: 'BinaryExpression',
          operator: node.operator,
          left,
          right,
          loc: copiedLocation(node),
        };
      }
      case 'CallExpression':
        return {
          type: 'CallExpression',
          callee: visitExpression(node.callee),
          arguments: node.arguments.map(visitExpression),
          loc: copiedLocation(node),
        };
      default:
        throw new TypeError(`unknown expression node type: ${node.type}`);
    }
  }

  const body = ast.body.map((statement) => {
    if (statement.type === 'LetStatement') {
      return {
        type: 'LetStatement',
        name: {
          type: 'Identifier',
          name: statement.name.name,
          loc: copiedLocation(statement.name),
        },
        initializer: visitExpression(statement.initializer),
        loc: copiedLocation(statement),
      };
    }
    if (statement.type === 'EmitStatement') {
      return {
        type: 'EmitStatement',
        expression: visitExpression(statement.expression),
        loc: copiedLocation(statement),
      };
    }
    throw new TypeError(`unknown statement node type: ${statement.type}`);
  });

  return { type: 'Program', body, loc: copiedLocation(ast) };
}

function encodeLiteral(value) {
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      throw new TypeError('cannot generate a non-finite numeric literal');
    }
    return Object.is(value, -0) ? '-0' : String(value);
  }
  if (typeof value === 'string') {
    return JSON.stringify(value)
      .replace(/\u2028/g, '\\u2028')
      .replace(/\u2029/g, '\\u2029');
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false';
  }
  throw new TypeError(`unsupported literal value: ${String(value)}`);
}

function generate(ast, suppliedAnalysis) {
  const analysis = suppliedAnalysis && suppliedAnalysis.ast === ast
    ? suppliedAnalysis
    : analyze(ast);

  function emitExpression(node) {
    switch (node.type) {
      case 'Literal':
        return encodeLiteral(node.value);
      case 'Identifier': {
        const id = analysis.referenceIds.get(node);
        if (!Number.isInteger(id)) {
          throw new TypeError(`identifier has no semantic binding: ${node.name}`);
        }
        return `v_${id}`;
      }
      case 'UnaryExpression':
        return `(${node.operator}${emitExpression(node.argument)})`;
      case 'BinaryExpression': {
        const operator = node.operator === '=='
          ? '==='
          : node.operator === '!=' ? '!==' : node.operator;
        return `(${emitExpression(node.left)} ${operator} ${emitExpression(node.right)})`;
      }
      case 'CallExpression': {
        if (node.callee.type !== 'Identifier' || !hasBuiltin(node.callee.name)) {
          throw new TypeError('unanalyzed call reached generator');
        }
        const target = BUILTINS[node.callee.name].js;
        return `${target}(${node.arguments.map(emitExpression).join(', ')})`;
      }
      default:
        throw new TypeError(`unknown expression node type: ${node.type}`);
    }
  }

  const lines = [
    '"use strict";',
    'const __output = [];',
    'const __len = (value) => {',
    '  if (typeof value !== "string") throw new TypeError("len expects a string");',
    '  return [...value].length;',
    '};',
  ];

  for (const statement of ast.body) {
    if (statement.type === 'LetStatement') {
      const id = analysis.declarationIds.get(statement);
      if (!Number.isInteger(id)) {
        throw new TypeError(`declaration has no semantic binding: ${statement.name.name}`);
      }
      lines.push(`const v_${id} = ${emitExpression(statement.initializer)};`);
    } else if (statement.type === 'EmitStatement') {
      lines.push(`__output.push(${emitExpression(statement.expression)});`);
    } else {
      throw new TypeError(`unknown statement node type: ${statement.type}`);
    }
  }
  lines.push('return __output;');
  return `${lines.join('\n')}\n`;
}

function interpret(sourceOrAst) {
  const ast = typeof sourceOrAst === 'string' ? parse(sourceOrAst) : sourceOrAst;
  const analysis = analyze(ast);
  const environment = new Map();
  const output = [];

  function evaluate(node) {
    switch (node.type) {
      case 'Literal':
        return node.value;
      case 'Identifier': {
        const id = analysis.referenceIds.get(node);
        if (!environment.has(id)) {
          throw new TypeError(`internal binding ${String(id)} has no runtime value`);
        }
        return environment.get(id);
      }
      case 'UnaryExpression':
        return evaluateUnary(node.operator, evaluate(node.argument));
      case 'BinaryExpression':
        if (node.operator === '&&') {
          const left = evaluate(node.left);
          return left && evaluate(node.right);
        }
        if (node.operator === '||') {
          const left = evaluate(node.left);
          return left || evaluate(node.right);
        }
        return evaluateBinary(node.operator, evaluate(node.left), evaluate(node.right));
      case 'CallExpression': {
        const spec = BUILTINS[node.callee.name];
        return spec.run(node.arguments.map(evaluate));
      }
      default:
        throw new TypeError(`unknown expression node type: ${node.type}`);
    }
  }

  for (const statement of ast.body) {
    if (statement.type === 'LetStatement') {
      environment.set(analysis.declarationIds.get(statement), evaluate(statement.initializer));
    } else if (statement.type === 'EmitStatement') {
      output.push(evaluate(statement.expression));
    }
  }
  return output;
}

function pipeline(source, options = {}) {
  const tokens = tokenize(source);
  const ast = parse(tokens);
  let optimizedAst = ast;
  let analysis = analyze(ast);
  const shouldOptimize = !Object.prototype.hasOwnProperty.call(options, 'optimize')
    || options.optimize !== false;
  if (shouldOptimize) {
    optimizedAst = optimize(ast);
    analysis = analyze(optimizedAst);
  }
  const code = generate(optimizedAst, analysis);
  return { tokens, ast, optimizedAst, analysis, code };
}

function compile(source, options = {}) {
  return pipeline(source, options).code;
}

module.exports = {
  CompilerError,
  tokenize,
  parse,
  analyze,
  optimize,
  generate,
  compile,
  interpret,
  pipeline,
};
