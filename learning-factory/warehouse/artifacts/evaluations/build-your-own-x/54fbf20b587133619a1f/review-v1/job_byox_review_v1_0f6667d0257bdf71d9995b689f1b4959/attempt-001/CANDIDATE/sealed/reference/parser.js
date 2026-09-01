import { ParseError } from "./errors.js";
import { TokenType, tokenize } from "./lexer.js";

const BINARY_OPERATOR = Object.freeze({
  [TokenType.PLUS]: "+",
  [TokenType.MINUS]: "-",
  [TokenType.STAR]: "*",
  [TokenType.SLASH]: "/",
  [TokenType.EQUAL_EQUAL]: "==",
  [TokenType.BANG_EQUAL]: "!=",
  [TokenType.LESS]: "<",
  [TokenType.LESS_EQUAL]: "<=",
  [TokenType.GREATER]: ">",
  [TokenType.GREATER_EQUAL]: ">=",
});

class Parser {
  constructor(tokens) {
    if (!Array.isArray(tokens) || tokens.length === 0) {
      throw new TypeError("parse expects source text or a non-empty token array");
    }
    if (tokens.at(-1)?.type !== TokenType.EOF) {
      throw new ParseError("token stream must end with EOF", tokens.at(-1));
    }
    this.tokens = tokens;
    this.current = 0;
  }

  parseProgram() {
    const body = [];
    while (!this.check(TokenType.EOF)) body.push(this.statement());
    this.consume(TokenType.EOF, "expected end of input");
    return { type: "Program", body };
  }

  statement() {
    if (this.match(TokenType.LET)) return this.letStatement();
    if (this.match(TokenType.SET)) return this.setStatement();
    if (this.match(TokenType.EMIT)) return this.emitStatement();
    if (this.match(TokenType.IF)) return this.ifStatement();
    if (this.match(TokenType.WHILE)) return this.whileStatement();
    throw this.error(this.peek(), "expected a statement");
  }

  letStatement() {
    const name = this.consume(TokenType.IDENTIFIER, "expected a variable name").lexeme;
    this.consume(TokenType.EQUAL, "expected '=' after variable name");
    const initializer = this.expression();
    this.consume(TokenType.SEMICOLON, "expected ';' after expression");
    return { type: "LetStatement", name, initializer };
  }

  setStatement() {
    const name = this.consume(TokenType.IDENTIFIER, "expected a variable name").lexeme;
    this.consume(TokenType.EQUAL, "expected '=' after variable name");
    const value = this.expression();
    this.consume(TokenType.SEMICOLON, "expected ';' after expression");
    return { type: "SetStatement", name, value };
  }

  emitStatement() {
    const expression = this.expression();
    this.consume(TokenType.SEMICOLON, "expected ';' after expression");
    return { type: "EmitStatement", expression };
  }

  ifStatement() {
    const condition = this.expression();
    const consequent = this.block();
    const alternate = this.match(TokenType.ELSE) ? this.block() : null;
    return { type: "IfStatement", condition, consequent, alternate };
  }

  whileStatement() {
    const condition = this.expression();
    const body = this.block();
    return { type: "WhileStatement", condition, body };
  }

  block() {
    this.consume(TokenType.LEFT_BRACE, "expected '{'");
    const body = [];
    while (!this.check(TokenType.RIGHT_BRACE) && !this.check(TokenType.EOF)) {
      body.push(this.statement());
    }
    this.consume(TokenType.RIGHT_BRACE, "expected '}' after block");
    return { type: "BlockStatement", body };
  }

  expression() {
    return this.equality();
  }

  equality() {
    let expression = this.comparison();
    while (this.match(TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL)) {
      const operator = BINARY_OPERATOR[this.previous().type];
      const right = this.comparison();
      expression = { type: "BinaryExpression", operator, left: expression, right };
    }
    return expression;
  }

  comparison() {
    let expression = this.term();
    while (this.match(TokenType.LESS, TokenType.LESS_EQUAL, TokenType.GREATER, TokenType.GREATER_EQUAL)) {
      const operator = BINARY_OPERATOR[this.previous().type];
      const right = this.term();
      expression = { type: "BinaryExpression", operator, left: expression, right };
    }
    return expression;
  }

  term() {
    let expression = this.factor();
    while (this.match(TokenType.PLUS, TokenType.MINUS)) {
      const operator = BINARY_OPERATOR[this.previous().type];
      const right = this.factor();
      expression = { type: "BinaryExpression", operator, left: expression, right };
    }
    return expression;
  }

  factor() {
    let expression = this.unary();
    while (this.match(TokenType.STAR, TokenType.SLASH)) {
      const operator = BINARY_OPERATOR[this.previous().type];
      const right = this.unary();
      expression = { type: "BinaryExpression", operator, left: expression, right };
    }
    return expression;
  }

  unary() {
    if (this.match(TokenType.MINUS, TokenType.BANG)) {
      const operator = this.previous().type === TokenType.MINUS ? "-" : "!";
      return { type: "UnaryExpression", operator, argument: this.unary() };
    }
    return this.primary();
  }

  primary() {
    if (this.match(TokenType.NUMBER)) {
      return { type: "NumberLiteral", value: this.previous().literal };
    }
    if (this.match(TokenType.TRUE, TokenType.FALSE)) {
      return { type: "BooleanLiteral", value: this.previous().type === TokenType.TRUE };
    }
    if (this.match(TokenType.IDENTIFIER)) {
      return { type: "Identifier", name: this.previous().lexeme };
    }
    if (this.match(TokenType.LEFT_PAREN)) {
      const expression = this.expression();
      this.consume(TokenType.RIGHT_PAREN, "expected ')' after expression");
      return expression;
    }
    throw this.error(this.peek(), "expected an expression");
  }

  match(...types) {
    for (const type of types) {
      if (this.check(type)) {
        this.advance();
        return true;
      }
    }
    return false;
  }

  consume(type, message) {
    if (this.check(type)) return this.advance();
    throw this.error(this.peek(), message);
  }

  check(type) {
    return this.peek()?.type === type;
  }

  advance() {
    if (this.current < this.tokens.length) this.current += 1;
    return this.previous();
  }

  peek() {
    return this.tokens[this.current] ?? this.tokens.at(-1);
  }

  previous() {
    return this.tokens[this.current - 1];
  }

  error(token, message) {
    return new ParseError(message, token);
  }
}

/** Parse source text or the public token array returned by tokenize(). */
export function parse(sourceOrTokens) {
  const tokens = typeof sourceOrTokens === "string" ? tokenize(sourceOrTokens) : sourceOrTokens;
  return new Parser(tokens).parseProgram();
}
