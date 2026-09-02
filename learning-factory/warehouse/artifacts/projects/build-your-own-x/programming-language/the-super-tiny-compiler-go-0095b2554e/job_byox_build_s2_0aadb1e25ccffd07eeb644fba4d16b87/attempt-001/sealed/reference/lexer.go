package prefixforge

import (
	"unicode/utf8"
)

type lexer struct {
	source string
	index  int
	line   int
	column int
	tokens []Token
}

func Tokenize(source string) ([]Token, error) {
	if len(source) > MaxSourceBytes {
		return nil, stageError("lex", initialSpan(), "source exceeds %d bytes", MaxSourceBytes)
	}
	if !utf8.ValidString(source) {
		offset := firstInvalidUTF8(source)
		at := positionAt(source, offset)
		end := at
		end.Offset++
		end.Column++
		return nil, stageError("lex", Span{Start: at, End: end}, "invalid UTF-8 encoding")
	}

	l := &lexer{source: source, line: 1, column: 1}
	for l.index < len(l.source) {
		b := l.source[l.index]
		switch {
		case isSpace(b):
			l.advance()
		case b == ';':
			l.skipComment()
		case b == '(':
			l.single(TokenLParen)
		case b == ')':
			l.single(TokenRParen)
		case b == '"':
			if err := l.scanString(); err != nil {
				return nil, err
			}
		case isDigit(b) || (b == '-' && l.index+1 < len(l.source) && isDigit(l.source[l.index+1])):
			l.scanNumber()
		case isLower(b):
			l.scanIdentifier()
		default:
			start := l.position()
			r, size := utf8.DecodeRuneInString(l.source[l.index:])
			for i := 0; i < size; i++ {
				l.advance()
			}
			return nil, stageError("lex", Span{Start: start, End: l.position()}, "unexpected character %q", r)
		}
	}
	p := l.position()
	l.tokens = append(l.tokens, Token{Kind: TokenEOF, At: Span{Start: p, End: p}})
	return l.tokens, nil
}

func (l *lexer) position() Position {
	return Position{Offset: l.index, Line: l.line, Column: l.column}
}

func (l *lexer) advance() byte {
	b := l.source[l.index]
	l.index++
	if b == '\n' {
		l.line++
		l.column = 1
	} else {
		l.column++
	}
	return b
}

func (l *lexer) single(kind TokenKind) {
	startIndex := l.index
	start := l.position()
	l.advance()
	l.tokens = append(l.tokens, Token{
		Kind:   kind,
		Lexeme: l.source[startIndex:l.index],
		At:     Span{Start: start, End: l.position()},
	})
}

func (l *lexer) skipComment() {
	for l.index < len(l.source) && l.source[l.index] != '\n' {
		l.advance()
	}
}

func (l *lexer) scanNumber() {
	startIndex := l.index
	start := l.position()
	if l.source[l.index] == '-' {
		l.advance()
	}
	for l.index < len(l.source) && isDigit(l.source[l.index]) {
		l.advance()
	}
	lexeme := l.source[startIndex:l.index]
	l.tokens = append(l.tokens, Token{
		Kind:   TokenNumber,
		Lexeme: lexeme,
		At:     Span{Start: start, End: l.position()},
	})
}

func (l *lexer) scanIdentifier() {
	startIndex := l.index
	start := l.position()
	for l.index < len(l.source) && isIdentifierContinue(l.source[l.index]) {
		l.advance()
	}
	lexeme := l.source[startIndex:l.index]
	l.tokens = append(l.tokens, Token{
		Kind:    TokenIdentifier,
		Lexeme:  lexeme,
		Literal: lexeme,
		At:      Span{Start: start, End: l.position()},
	})
}

func (l *lexer) scanString() error {
	startIndex := l.index
	start := l.position()
	l.advance() // opening quote
	literal := make([]byte, 0, 16)

	for l.index < len(l.source) {
		switch l.source[l.index] {
		case '"':
			l.advance()
			l.tokens = append(l.tokens, Token{
				Kind:    TokenString,
				Lexeme:  l.source[startIndex:l.index],
				Literal: string(literal),
				At:      Span{Start: start, End: l.position()},
			})
			return nil
		case '\\':
			escapeStart := l.position()
			l.advance()
			if l.index == len(l.source) {
				return stageError("lex", Span{Start: start, End: l.position()}, "unterminated string")
			}
			escaped := l.advance()
			switch escaped {
			case '"':
				literal = append(literal, '"')
			case '\\':
				literal = append(literal, '\\')
			case 'n':
				literal = append(literal, '\n')
			case 'r':
				literal = append(literal, '\r')
			case 't':
				literal = append(literal, '\t')
			default:
				return stageError("lex", Span{Start: escapeStart, End: l.position()}, "invalid escape \\%c", escaped)
			}
		default:
			literal = append(literal, l.advance())
		}
	}
	return stageError("lex", Span{Start: start, End: l.position()}, "unterminated string")
}

func isSpace(b byte) bool {
	return b == ' ' || b == '\t' || b == '\r' || b == '\n'
}

func isDigit(b byte) bool { return b >= '0' && b <= '9' }
func isLower(b byte) bool { return b >= 'a' && b <= 'z' }

func isIdentifierContinue(b byte) bool {
	return isLower(b) || isDigit(b) || b == '_' || b == '-'
}

func firstInvalidUTF8(source string) int {
	for offset := 0; offset < len(source); {
		_, size := utf8.DecodeRuneInString(source[offset:])
		if size == 1 && source[offset] >= utf8.RuneSelf {
			return offset
		}
		offset += size
	}
	return len(source)
}

func positionAt(source string, offset int) Position {
	p := Position{Line: 1, Column: 1}
	for i := 0; i < offset; i++ {
		p.Offset++
		if source[i] == '\n' {
			p.Line++
			p.Column = 1
		} else {
			p.Column++
		}
	}
	return p
}
