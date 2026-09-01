import { LexerError } from "./errors.js";

export const TokenType = Object.freeze({
  LEFT_PAREN: "LEFT_PAREN",
  RIGHT_PAREN: "RIGHT_PAREN",
  LEFT_BRACE: "LEFT_BRACE",
  RIGHT_BRACE: "RIGHT_BRACE",
  SEMICOLON: "SEMICOLON",
  PLUS: "PLUS",
  MINUS: "MINUS",
  STAR: "STAR",
  SLASH: "SLASH",
  BANG: "BANG",
  BANG_EQUAL: "BANG_EQUAL",
  EQUAL: "EQUAL",
  EQUAL_EQUAL: "EQUAL_EQUAL",
  GREATER: "GREATER",
  GREATER_EQUAL: "GREATER_EQUAL",
  LESS: "LESS",
  LESS_EQUAL: "LESS_EQUAL",
  IDENTIFIER: "IDENTIFIER",
  NUMBER: "NUMBER",
  LET: "LET",
  SET: "SET",
  EMIT: "EMIT",
  IF: "IF",
  ELSE: "ELSE",
  WHILE: "WHILE",
  TRUE: "TRUE",
  FALSE: "FALSE",
  EOF: "EOF",
});

const KEYWORDS = Object.freeze({
  let: TokenType.LET,
  set: TokenType.SET,
  emit: TokenType.EMIT,
  if: TokenType.IF,
  else: TokenType.ELSE,
  while: TokenType.WHILE,
  true: TokenType.TRUE,
  false: TokenType.FALSE,
});

const SINGLE_CHARACTER_TYPES = Object.freeze({
  "(": TokenType.LEFT_PAREN,
  ")": TokenType.RIGHT_PAREN,
  "{": TokenType.LEFT_BRACE,
  "}": TokenType.RIGHT_BRACE,
  ";": TokenType.SEMICOLON,
  "+": TokenType.PLUS,
  "-": TokenType.MINUS,
  "*": TokenType.STAR,
  "/": TokenType.SLASH,
});

function isDigit(character) {
  return character >= "0" && character <= "9";
}

function isIdentifierStart(character) {
  return (character >= "a" && character <= "z")
    || (character >= "A" && character <= "Z")
    || character === "_";
}

function isIdentifierPart(character) {
  return isIdentifierStart(character) || isDigit(character);
}

/** Convert Pebble source text into position-bearing public token records. */
export function tokenize(source) {
  if (typeof source !== "string") {
    throw new TypeError("tokenize expects source text");
  }

  const tokens = [];
  let offset = 0;
  let line = 1;
  let column = 1;

  const peek = (distance = 0) => source[offset + distance] ?? "\0";
  const advance = () => {
    const character = source[offset] ?? "\0";
    offset += 1;
    if (character === "\n") {
      line += 1;
      column = 1;
    } else {
      column += 1;
    }
    return character;
  };
  const add = (type, lexeme, literal, start) => {
    tokens.push({ type, lexeme, literal, line: start.line, column: start.column });
  };

  while (offset < source.length) {
    const character = peek();

    if (character === " " || character === "\t" || character === "\r" || character === "\n") {
      advance();
      continue;
    }

    if (character === "/" && peek(1) === "/") {
      while (offset < source.length && peek() !== "\n") advance();
      continue;
    }

    const start = { line, column, offset };

    if (isDigit(character)) {
      while (isDigit(peek())) advance();
      if (peek() === "." && isDigit(peek(1))) {
        advance();
        while (isDigit(peek())) advance();
      }
      const lexeme = source.slice(start.offset, offset);
      const literal = Number(lexeme);
      if (!Number.isFinite(literal)) {
        throw new LexerError("numeric literal is not finite", start, "INVALID_NUMBER");
      }
      add(TokenType.NUMBER, lexeme, literal, start);
      continue;
    }

    if (isIdentifierStart(character)) {
      while (isIdentifierPart(peek())) advance();
      const lexeme = source.slice(start.offset, offset);
      const type = Object.hasOwn(KEYWORDS, lexeme) ? KEYWORDS[lexeme] : TokenType.IDENTIFIER;
      const literal = type === TokenType.TRUE ? true : type === TokenType.FALSE ? false : null;
      add(type, lexeme, literal, start);
      continue;
    }

    const singleType = SINGLE_CHARACTER_TYPES[character];
    if (singleType !== undefined) {
      add(singleType, advance(), null, start);
      continue;
    }

    const twoCharacter = `${character}${peek(1)}`;
    const pairedType = {
      "!=": TokenType.BANG_EQUAL,
      "==": TokenType.EQUAL_EQUAL,
      ">=": TokenType.GREATER_EQUAL,
      "<=": TokenType.LESS_EQUAL,
    }[twoCharacter];
    if (pairedType !== undefined) {
      advance();
      advance();
      add(pairedType, twoCharacter, null, start);
      continue;
    }

    const operatorType = {
      "!": TokenType.BANG,
      "=": TokenType.EQUAL,
      ">": TokenType.GREATER,
      "<": TokenType.LESS,
    }[character];
    if (operatorType !== undefined) {
      add(operatorType, advance(), null, start);
      continue;
    }

    throw new LexerError(`unexpected character ${JSON.stringify(character)}`, start);
  }

  tokens.push({ type: TokenType.EOF, lexeme: "", literal: null, line, column });
  return tokens;
}
