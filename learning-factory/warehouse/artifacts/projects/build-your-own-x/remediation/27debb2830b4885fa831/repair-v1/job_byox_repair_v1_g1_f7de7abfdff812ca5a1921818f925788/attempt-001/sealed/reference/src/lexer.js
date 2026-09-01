import { LexError, boundedInteger } from "./errors.js";
import { KEYWORDS, TokenType as T } from "./tokens.js";

const MAX_SOURCE_LENGTH = 1_000_000;
const MAX_TOKENS = 200_000;

export function tokenize(source, options = {}) {
  if (typeof source !== "string") throw new TypeError("source must be a string");
  const maxSourceLength = boundedInteger(options, "maxSourceLength", MAX_SOURCE_LENGTH);
  const maxTokens = boundedInteger(options, "maxTokens", MAX_TOKENS);
  if (source.length > maxSourceLength) {
    throw new LexError(`Source exceeds ${maxSourceLength} code units`, { line: 1, column: 1 });
  }
  return new Scanner(source, maxTokens).scan();
}

class Scanner {
  constructor(source, maxTokens) {
    this.source = source;
    this.maxTokens = maxTokens;
    this.tokens = [];
    this.start = 0;
    this.current = 0;
    this.line = 1;
    this.column = 1;
    this.startLine = 1;
    this.startColumn = 1;
  }

  scan() {
    while (!this._atEnd()) {
      this.start = this.current;
      this.startLine = this.line;
      this.startColumn = this.column;
      this._scanToken();
    }
    this.tokens.push({
      type: T.EOF,
      lexeme: "",
      literal: null,
      line: this.line,
      column: this.column
    });
    return this.tokens;
  }

  _scanToken() {
    const c = this._advance();
    const simple = {
      "(": T.LEFT_PAREN,
      ")": T.RIGHT_PAREN,
      "{": T.LEFT_BRACE,
      "}": T.RIGHT_BRACE,
      ";": T.SEMICOLON,
      "+": T.PLUS,
      "-": T.MINUS,
      "*": T.STAR
    };
    if (simple[c]) return this._add(simple[c]);

    switch (c) {
      case "!": return this._add(this._match("=") ? T.BANG_EQUAL : T.BANG);
      case "=": return this._add(this._match("=") ? T.EQUAL_EQUAL : T.EQUAL);
      case "<": return this._add(this._match("=") ? T.LESS_EQUAL : T.LESS);
      case ">": return this._add(this._match("=") ? T.GREATER_EQUAL : T.GREATER);
      case "/":
        if (this._match("/")) {
          while (!this._atEnd() && this._peek() !== "\n" && this._peek() !== "\r") this._advance();
          return;
        }
        return this._add(T.SLASH);
      case " ":
      case "\t":
        return;
      case "\n":
        return;
      case "\r":
        if (this._peek() === "\n") {
          this._advance();
        } else {
          this.line += 1;
          this.column = 1;
        }
        return;
      case '"': return this._string();
      default:
        if (isDigit(c)) return this._number();
        if (isAlpha(c)) return this._identifier();
        throw new LexError(`Unexpected character ${JSON.stringify(c)}`, this._startLocation());
    }
  }

  _string() {
    let value = "";
    while (!this._atEnd()) {
      const location = { line: this.line, column: this.column };
      const c = this._advance();
      if (c === '"') {
        this._add(T.STRING, value);
        return;
      }
      if (c === "\n" || c === "\r") {
        throw new LexError("Raw line break in string", location);
      }
      if (c !== "\\") {
        value += c;
        continue;
      }
      if (this._atEnd()) throw new LexError("Unterminated string", this._startLocation());
      const escapeLocation = { line: this.line, column: this.column };
      const escaped = this._advance();
      const escapes = { '"': '"', "\\": "\\", n: "\n", r: "\r", t: "\t" };
      if (!Object.prototype.hasOwnProperty.call(escapes, escaped)) {
        throw new LexError(`Unsupported escape \\${escaped}`, escapeLocation);
      }
      value += escapes[escaped];
    }
    throw new LexError("Unterminated string", this._startLocation());
  }

  _number() {
    while (isDigit(this._peek())) this._advance();
    if (this._peek() === "." && isDigit(this._peekNext())) {
      this._advance();
      while (isDigit(this._peek())) this._advance();
    }
    const value = Number(this.source.slice(this.start, this.current));
    if (!Number.isFinite(value)) throw new LexError("Number is not finite", this._startLocation());
    this._add(T.NUMBER, value);
  }

  _identifier() {
    while (isAlphaNumeric(this._peek())) this._advance();
    const text = this.source.slice(this.start, this.current);
    const type = Object.prototype.hasOwnProperty.call(KEYWORDS, text)
      ? KEYWORDS[text]
      : T.IDENTIFIER;
    this._add(type);
  }

  _add(type, literal = null) {
    if (this.tokens.length >= this.maxTokens) {
      throw new LexError(`Token count exceeds ${this.maxTokens}`, this._startLocation());
    }
    this.tokens.push({
      type,
      lexeme: this.source.slice(this.start, this.current),
      literal,
      line: this.startLine,
      column: this.startColumn
    });
  }

  _advance() {
    const c = this.source[this.current++];
    if (c === "\n") {
      this.line += 1;
      this.column = 1;
    } else {
      this.column += 1;
    }
    return c;
  }

  _match(expected) {
    if (this._atEnd() || this.source[this.current] !== expected) return false;
    this._advance();
    return true;
  }

  _peek() { return this._atEnd() ? "\0" : this.source[this.current]; }
  _peekNext() { return this.current + 1 >= this.source.length ? "\0" : this.source[this.current + 1]; }
  _atEnd() { return this.current >= this.source.length; }
  _startLocation() { return { line: this.startLine, column: this.startColumn }; }
}

function isDigit(c) { return c >= "0" && c <= "9"; }
function isAlpha(c) { return (c >= "a" && c <= "z") || (c >= "A" && c <= "Z") || c === "_"; }
function isAlphaNumeric(c) { return isAlpha(c) || isDigit(c); }
