import { ParseError, boundedInteger } from "./errors.js";
import { TokenType as T } from "./tokens.js";

const MAX_PARSE_DEPTH = 1_000;

export function parse(tokens, options = {}) {
  if (!Array.isArray(tokens)) throw new TypeError("tokens must be an array");
  const maxParseDepth = boundedInteger(options, "maxParseDepth", MAX_PARSE_DEPTH);
  return new Parser(tokens, maxParseDepth).parse();
}

class Parser {
  constructor(tokens, maxDepth) {
    this.tokens = tokens;
    this.maxDepth = maxDepth;
    this.current = 0;
    this.depth = 0;
    if (tokens.length === 0 || tokens[tokens.length - 1]?.type !== T.EOF) {
      throw new ParseError("Token stream must end with EOF", tokenLocation(tokens.at(-1)));
    }
  }

  parse() {
    const start = tokenLocation(this._peek());
    const body = [];
    while (!this._check(T.EOF)) body.push(this._statementGuarded());
    this._consume(T.EOF, "Expected end of input");
    if (this.current !== this.tokens.length) {
      throw new ParseError("Tokens found after EOF", tokenLocation(this.tokens[this.current]));
    }
    return { type: "Program", body, loc: start };
  }

  _statementGuarded() { return this._guard(() => this._statement()); }

  _statement() {
    if (this._match(T.LET)) return this._letStatement(this._previous());
    if (this._match(T.PRINT)) return this._printStatement(this._previous());
    if (this._match(T.IF)) return this._ifStatement(this._previous());
    if (this._match(T.WHILE)) return this._whileStatement(this._previous());
    if (this._match(T.LEFT_BRACE)) return this._block(this._previous());
    return this._expressionStatement();
  }

  _letStatement(keyword) {
    const nameToken = this._consume(T.IDENTIFIER, "Expected variable name after 'let'");
    this._consume(T.EQUAL, "Expected '=' after variable name");
    const initializer = this._expression();
    this._consume(T.SEMICOLON, "Expected ';' after declaration");
    return {
      type: "LetStatement",
      name: identifier(nameToken),
      initializer,
      loc: tokenLocation(keyword)
    };
  }

  _printStatement(keyword) {
    const expression = this._expression();
    this._consume(T.SEMICOLON, "Expected ';' after printed expression");
    return { type: "PrintStatement", expression, loc: tokenLocation(keyword) };
  }

  _expressionStatement() {
    const expression = this._expression();
    this._consume(T.SEMICOLON, "Expected ';' after expression");
    return { type: "ExpressionStatement", expression, loc: expression.loc };
  }

  _ifStatement(keyword) {
    this._consume(T.LEFT_PAREN, "Expected '(' after 'if'");
    const test = this._expression();
    this._consume(T.RIGHT_PAREN, "Expected ')' after condition");
    const open = this._consume(T.LEFT_BRACE, "Expected block after if condition");
    const consequent = this._block(open);
    let alternate = null;
    if (this._match(T.ELSE)) {
      const elseOpen = this._consume(T.LEFT_BRACE, "Expected block after 'else'");
      alternate = this._block(elseOpen);
    }
    return { type: "IfStatement", test, consequent, alternate, loc: tokenLocation(keyword) };
  }

  _whileStatement(keyword) {
    this._consume(T.LEFT_PAREN, "Expected '(' after 'while'");
    const test = this._expression();
    this._consume(T.RIGHT_PAREN, "Expected ')' after condition");
    const open = this._consume(T.LEFT_BRACE, "Expected block after while condition");
    return { type: "WhileStatement", test, body: this._block(open), loc: tokenLocation(keyword) };
  }

  _block(open) {
    const body = [];
    while (!this._check(T.RIGHT_BRACE) && !this._check(T.EOF)) body.push(this._statementGuarded());
    this._consume(T.RIGHT_BRACE, "Expected '}' after block");
    return { type: "BlockStatement", body, loc: tokenLocation(open) };
  }

  _expression() { return this._guard(() => this._assignment()); }

  _assignment() {
    const left = this._or();
    if (!this._match(T.EQUAL)) return left;
    const equals = this._previous();
    const value = this._guard(() => this._assignment());
    if (left.type !== "Identifier") {
      throw new ParseError("Invalid assignment target", tokenLocation(equals));
    }
    return { type: "AssignmentExpression", name: left, value, loc: left.loc };
  }

  _or() {
    let expression = this._and();
    while (this._match(T.OR)) {
      const operator = this._previous();
      expression = binaryNode("LogicalExpression", expression, operator, this._and());
    }
    return expression;
  }

  _and() {
    let expression = this._equality();
    while (this._match(T.AND)) {
      const operator = this._previous();
      expression = binaryNode("LogicalExpression", expression, operator, this._equality());
    }
    return expression;
  }

  _equality() {
    let expression = this._comparison();
    while (this._match(T.EQUAL_EQUAL, T.BANG_EQUAL)) {
      const operator = this._previous();
      expression = binaryNode("BinaryExpression", expression, operator, this._comparison());
    }
    return expression;
  }

  _comparison() {
    let expression = this._term();
    while (this._match(T.GREATER, T.GREATER_EQUAL, T.LESS, T.LESS_EQUAL)) {
      const operator = this._previous();
      expression = binaryNode("BinaryExpression", expression, operator, this._term());
    }
    return expression;
  }

  _term() {
    let expression = this._factor();
    while (this._match(T.PLUS, T.MINUS)) {
      const operator = this._previous();
      expression = binaryNode("BinaryExpression", expression, operator, this._factor());
    }
    return expression;
  }

  _factor() {
    let expression = this._unary();
    while (this._match(T.STAR, T.SLASH)) {
      const operator = this._previous();
      expression = binaryNode("BinaryExpression", expression, operator, this._unary());
    }
    return expression;
  }

  _unary() {
    if (this._match(T.BANG, T.MINUS)) {
      const operator = this._previous();
      return {
        type: "UnaryExpression",
        operator: operator.lexeme,
        argument: this._guard(() => this._unary()),
        loc: tokenLocation(operator)
      };
    }
    return this._primary();
  }

  _primary() {
    if (this._match(T.FALSE)) return literal(false, this._previous());
    if (this._match(T.TRUE)) return literal(true, this._previous());
    if (this._match(T.NULL)) return literal(null, this._previous());
    if (this._match(T.NUMBER, T.STRING)) return literal(this._previous().literal, this._previous());
    if (this._match(T.IDENTIFIER)) return identifier(this._previous());
    if (this._match(T.LEFT_PAREN)) {
      const expression = this._expression();
      this._consume(T.RIGHT_PAREN, "Expected ')' after expression");
      return expression;
    }
    throw new ParseError("Expected expression", tokenLocation(this._peek()));
  }

  _guard(callback) {
    this.depth += 1;
    if (this.depth > this.maxDepth) {
      this.depth -= 1;
      throw new ParseError(`Parse depth exceeds ${this.maxDepth}`, tokenLocation(this._peek()));
    }
    try { return callback(); } finally { this.depth -= 1; }
  }

  _match(...types) {
    for (const type of types) {
      if (this._check(type)) { this._advance(); return true; }
    }
    return false;
  }

  _consume(type, message) {
    if (this._check(type)) return this._advance();
    throw new ParseError(message, tokenLocation(this._peek()));
  }

  _check(type) { return this._peek()?.type === type; }
  _advance() { if (this.current < this.tokens.length) this.current += 1; return this._previous(); }
  _peek() { return this.tokens[this.current]; }
  _previous() { return this.tokens[this.current - 1]; }
}

function tokenLocation(token) {
  return {
    line: Number.isInteger(token?.line) ? token.line : null,
    column: Number.isInteger(token?.column) ? token.column : null
  };
}
function identifier(token) { return { type: "Identifier", name: token.lexeme, loc: tokenLocation(token) }; }
function literal(value, token) { return { type: "Literal", value, loc: tokenLocation(token) }; }
function binaryNode(type, left, operator, right) {
  return { type, operator: operator.lexeme, left, right, loc: tokenLocation(operator) };
}
