import { MicaSyntaxError, mergeSpans, spanFrom } from "./diagnostics.mjs";
import { TokenType } from "./tokens.mjs";

export function parse(tokens) {
  if (!Array.isArray(tokens) || tokens.length === 0) {
    throw new TypeError("parse expects a non-empty token array");
  }

  let current = 0;
  const peek = () => tokens[Math.min(current, tokens.length - 1)];
  const previous = () => tokens[current - 1];
  const check = (type) => peek()?.type === type;
  const atEnd = () => check(TokenType.EOF);
  const advance = () => {
    const token = peek();
    if (!atEnd()) current += 1;
    return token;
  };
  const match = (...types) => {
    for (const type of types) {
      if (check(type)) {
        advance();
        return true;
      }
    }
    return false;
  };
  const fail = (token, message, code = "E_EXPECTED_TOKEN") => {
    throw new MicaSyntaxError(code, message, token?.span ?? null);
  };
  const consume = (type, message) => {
    if (check(type)) return advance();
    return fail(peek(), message);
  };

  const primary = () => {
    if (match(TokenType.FALSE)) {
      const token = previous();
      return { type: "Literal", value: false, raw: token.lexeme, span: token.span };
    }
    if (match(TokenType.TRUE)) {
      const token = previous();
      return { type: "Literal", value: true, raw: token.lexeme, span: token.span };
    }
    if (match(TokenType.NIL)) {
      const token = previous();
      return { type: "Literal", value: null, raw: token.lexeme, span: token.span };
    }
    if (match(TokenType.NUMBER, TokenType.STRING)) {
      const token = previous();
      return { type: "Literal", value: token.literal, raw: token.lexeme, span: token.span };
    }
    if (match(TokenType.IDENTIFIER)) {
      const token = previous();
      return { type: "Identifier", name: token.lexeme, span: token.span };
    }
    if (match(TokenType.LEFT_PAREN)) {
      const open = previous();
      const expression = assignment();
      const close = consume(TokenType.RIGHT_PAREN, "expected ')' after expression");
      return { ...expression, grouped: true, span: mergeSpans(open.span, close.span) };
    }
    return fail(peek(), "expected expression");
  };

  const unary = () => {
    if (match(TokenType.BANG, TokenType.MINUS)) {
      const operator = previous();
      const argument = unary();
      return {
        type: "UnaryExpression",
        operator: operator.lexeme,
        argument,
        span: mergeSpans(operator.span, argument.span),
      };
    }
    return primary();
  };

  const binaryLevel = (operand, types) => {
    let expression = operand();
    while (match(...types)) {
      const operator = previous();
      const right = operand();
      expression = {
        type: "BinaryExpression",
        operator: operator.lexeme,
        left: expression,
        right,
        span: mergeSpans(expression.span, right.span),
      };
    }
    return expression;
  };

  const factor = () => binaryLevel(unary, [TokenType.STAR, TokenType.SLASH]);
  const term = () => binaryLevel(factor, [TokenType.PLUS, TokenType.MINUS]);
  const comparison = () =>
    binaryLevel(term, [
      TokenType.GREATER,
      TokenType.GREATER_EQUAL,
      TokenType.LESS,
      TokenType.LESS_EQUAL,
    ]);
  const equality = () =>
    binaryLevel(comparison, [TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL]);

  function assignment() {
    const target = equality();
    if (!match(TokenType.EQUAL)) return target;
    const equals = previous();
    const value = assignment();
    if (target.type !== "Identifier" || target.grouped === true) {
      return fail(equals, "assignment target must be an identifier", "E_INVALID_ASSIGNMENT");
    }
    return {
      type: "AssignmentExpression",
      name: target.name,
      value,
      span: mergeSpans(target.span, value.span),
    };
  }

  const expressionStatement = () => {
    const expression = assignment();
    const semicolon = consume(TokenType.SEMICOLON, "expected ';' after expression");
    return {
      type: "ExpressionStatement",
      expression,
      span: mergeSpans(expression.span, semicolon.span),
    };
  };

  const printStatement = (keyword) => {
    const expression = assignment();
    const semicolon = consume(TokenType.SEMICOLON, "expected ';' after printed expression");
    return {
      type: "PrintStatement",
      expression,
      span: mergeSpans(keyword.span, semicolon.span),
    };
  };

  const blockStatement = (open) => {
    const body = [];
    while (!check(TokenType.RIGHT_BRACE) && !atEnd()) body.push(declaration());
    const close = consume(TokenType.RIGHT_BRACE, "expected '}' after block");
    return { type: "BlockStatement", body, span: mergeSpans(open.span, close.span) };
  };

  const ifStatement = (keyword) => {
    consume(TokenType.LEFT_PAREN, "expected '(' after 'if'");
    const test = assignment();
    consume(TokenType.RIGHT_PAREN, "expected ')' after condition");
    const thenOpen = consume(TokenType.LEFT_BRACE, "expected '{' before then branch");
    const consequent = blockStatement(thenOpen);
    let alternate = null;
    if (match(TokenType.ELSE)) {
      const elseOpen = consume(TokenType.LEFT_BRACE, "expected '{' before else branch");
      alternate = blockStatement(elseOpen);
    }
    return {
      type: "IfStatement",
      test,
      consequent,
      alternate,
      span: spanFrom(keyword.span.start, (alternate ?? consequent).span.end),
    };
  };

  function statement() {
    if (match(TokenType.PRINT)) return printStatement(previous());
    if (match(TokenType.IF)) return ifStatement(previous());
    if (match(TokenType.LEFT_BRACE)) return blockStatement(previous());
    return expressionStatement();
  }

  function declaration() {
    if (!match(TokenType.LET)) return statement();
    const keyword = previous();
    const nameToken = consume(TokenType.IDENTIFIER, "expected binding name after 'let'");
    consume(TokenType.EQUAL, "expected '=' after binding name");
    const initializer = assignment();
    const semicolon = consume(TokenType.SEMICOLON, "expected ';' after binding declaration");
    return {
      type: "LetStatement",
      name: { type: "Identifier", name: nameToken.lexeme, span: nameToken.span },
      initializer,
      span: mergeSpans(keyword.span, semicolon.span),
    };
  }

  const body = [];
  const start = peek().span?.start;
  while (!atEnd()) body.push(declaration());
  const eof = consume(TokenType.EOF, "expected end of input");
  if (current !== tokens.length - 1) fail(eof, "tokens found after EOF");
  return {
    type: "Program",
    body,
    span: spanFrom(start, eof.span.end),
  };
}
