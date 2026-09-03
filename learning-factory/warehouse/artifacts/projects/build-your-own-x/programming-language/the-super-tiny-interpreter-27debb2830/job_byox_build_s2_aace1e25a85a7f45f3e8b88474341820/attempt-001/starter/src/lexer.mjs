import { MicaSyntaxError, spanFrom } from "./diagnostics.mjs";
import { KEYWORDS, TokenType } from "./tokens.mjs";

const isDigit = (character) => character >= "0" && character <= "9";
const isAlpha = (character) =>
  (character >= "a" && character <= "z") ||
  (character >= "A" && character <= "Z") ||
  character === "_";
const isAlphaNumeric = (character) => isAlpha(character) || isDigit(character);

export function tokenize(source) {
  if (typeof source !== "string") {
    throw new TypeError("tokenize expects a string");
  }

  const tokens = [];
  let startOffset = 0;
  let startPosition = null;
  let current = 0;
  let line = 1;
  let column = 1;

  const atEnd = () => current >= source.length;
  const position = () => ({ offset: current, line, column });
  const peek = () => (atEnd() ? "\0" : source[current]);
  const peekNext = () => (current + 1 >= source.length ? "\0" : source[current + 1]);
  const advance = () => {
    const character = source[current++];
    if (character === "\n") {
      line += 1;
      column = 1;
    } else {
      column += 1;
    }
    return character;
  };
  const match = (expected) => {
    if (atEnd() || source[current] !== expected) return false;
    advance();
    return true;
  };
  const add = (type, literal = null) => {
    tokens.push({
      type,
      lexeme: source.slice(startOffset, current),
      literal,
      span: spanFrom(startPosition, position()),
    });
  };
  const fail = (code, message, start = startPosition) => {
    throw new MicaSyntaxError(code, message, spanFrom(start, position()));
  };

  const scanString = () => {
    let decoded = "";
    while (!atEnd() && peek() !== '"') {
      if (peek() !== "\\") {
        decoded += advance();
        continue;
      }

      const escapeStart = position();
      advance();
      if (atEnd()) fail("E_UNTERMINATED_STRING", "unterminated string", startPosition);
      const escape = advance();
      const escapes = { n: "\n", r: "\r", t: "\t", '"': '"', "\\": "\\" };
      if (!Object.hasOwn(escapes, escape)) {
        fail("E_INVALID_ESCAPE", `unsupported escape \\${escape}`, escapeStart);
      }
      decoded += escapes[escape];
    }

    if (atEnd()) fail("E_UNTERMINATED_STRING", "unterminated string", startPosition);
    advance();
    add(TokenType.STRING, decoded);
  };

  const scanNumber = () => {
    while (isDigit(peek())) advance();
    if (peek() === "." && isDigit(peekNext())) {
      advance();
      while (isDigit(peek())) advance();
    }
    const value = Number(source.slice(startOffset, current));
    if (!Number.isFinite(value)) fail("E_INVALID_NUMBER", "number must be finite");
    add(TokenType.NUMBER, value);
  };

  const scanIdentifier = () => {
    while (isAlphaNumeric(peek())) advance();
    const text = source.slice(startOffset, current);
    add(KEYWORDS[text] ?? TokenType.IDENTIFIER, null);
  };

  while (!atEnd()) {
    startOffset = current;
    startPosition = position();
    const character = advance();
    switch (character) {
      case "(": add(TokenType.LEFT_PAREN); break;
      case ")": add(TokenType.RIGHT_PAREN); break;
      case "{": add(TokenType.LEFT_BRACE); break;
      case "}": add(TokenType.RIGHT_BRACE); break;
      case ";": add(TokenType.SEMICOLON); break;
      case "+": add(TokenType.PLUS); break;
      case "-": add(TokenType.MINUS); break;
      case "*": add(TokenType.STAR); break;
      case "!": add(match("=") ? TokenType.BANG_EQUAL : TokenType.BANG); break;
      case "=": add(match("=") ? TokenType.EQUAL_EQUAL : TokenType.EQUAL); break;
      case "<": add(match("=") ? TokenType.LESS_EQUAL : TokenType.LESS); break;
      case ">": add(match("=") ? TokenType.GREATER_EQUAL : TokenType.GREATER); break;
      case "/":
        if (match("/")) {
          while (!atEnd() && peek() !== "\n") advance();
        } else {
          add(TokenType.SLASH);
        }
        break;
      case " ":
      case "\r":
      case "\t":
      case "\n":
        break;
      case '"': scanString(); break;
      default:
        if (isDigit(character)) scanNumber();
        else if (isAlpha(character)) scanIdentifier();
        else fail("E_UNEXPECTED_CHARACTER", `unexpected character ${JSON.stringify(character)}`);
    }
  }

  const end = position();
  tokens.push({ type: TokenType.EOF, lexeme: "", literal: null, span: spanFrom(end, end) });
  return tokens;
}
