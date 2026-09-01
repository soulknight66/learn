package pebble

import "strconv"

type scanner struct {
	source string
	offset int
	line   int
	column int
}

func Scan(source string) ([]Token, error) {
	s := scanner{source: source, line: 1, column: 1}
	tokens := make([]Token, 0)
	for {
		s.skipIgnored()
		if s.offset == len(s.source) {
			pos := s.position()
			return append(tokens, Token{Kind: TokenEOF, Span: Span{Start: pos, End: pos}}), nil
		}

		start := s.position()
		startOffset := s.offset
		ch := s.source[s.offset]
		var kind TokenKind
		switch ch {
		case '(':
			kind = TokenLParen
		case ')':
			kind = TokenRParen
		case '+':
			kind = TokenPlus
		case '-':
			kind = TokenMinus
		case '*':
			kind = TokenStar
		case '/':
			kind = TokenSlash
		default:
			if isDigit(ch) {
				for s.offset < len(s.source) && isDigit(s.source[s.offset]) {
					s.advance()
				}
				lexeme := s.source[startOffset:s.offset]
				value, err := strconv.ParseInt(lexeme, 10, 64)
				if err != nil {
					return nil, languageError(StageScan, CodeIntegerRange, start, "integer literal is outside signed 64-bit range")
				}
				tokens = append(tokens, Token{
					Kind: TokenInteger, Lexeme: lexeme, Integer: value,
					Span: Span{Start: start, End: s.position()},
				})
				continue
			}
			if isIdentifierStart(ch) {
				for s.offset < len(s.source) && isIdentifierContinue(s.source[s.offset]) {
					s.advance()
				}
				lexeme := s.source[startOffset:s.offset]
				kind := TokenIdentifier
				if lexeme == "let" {
					kind = TokenLet
				} else if lexeme == "print" {
					kind = TokenPrint
				}
				tokens = append(tokens, Token{Kind: kind, Lexeme: lexeme, Span: Span{Start: start, End: s.position()}})
				continue
			}
			return nil, languageError(StageScan, CodeInvalidChar, start, "unexpected source byte")
		}

		s.advance()
		tokens = append(tokens, Token{
			Kind: kind, Lexeme: s.source[startOffset:s.offset],
			Span: Span{Start: start, End: s.position()},
		})
	}
}

func (s *scanner) position() Position {
	return Position{Offset: s.offset, Line: s.line, Column: s.column}
}

func (s *scanner) advance() {
	ch := s.source[s.offset]
	s.offset++
	if ch == '\n' {
		s.line++
		s.column = 1
	} else {
		s.column++
	}
}

func (s *scanner) skipIgnored() {
	for s.offset < len(s.source) {
		switch s.source[s.offset] {
		case ' ', '\t', '\r', '\n':
			s.advance()
		case '#':
			for s.offset < len(s.source) && s.source[s.offset] != '\n' {
				s.advance()
			}
		default:
			return
		}
	}
}

func isDigit(ch byte) bool {
	return ch >= '0' && ch <= '9'
}

func isIdentifierStart(ch byte) bool {
	return ch >= 'a' && ch <= 'z' || ch >= 'A' && ch <= 'Z' || ch == '_'
}

func isIdentifierContinue(ch byte) bool {
	return isIdentifierStart(ch) || isDigit(ch)
}
