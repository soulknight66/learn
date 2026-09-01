package pebble

import "strconv"

type parser struct {
	tokens []Token
	index  int
}

func Parse(tokens []Token) (Program, error) {
	if err := validateTokenStream(tokens); err != nil {
		return Program{}, err
	}
	p := parser{tokens: tokens}
	statements := make([]Stmt, 0)
	for p.current().Kind != TokenEOF {
		statement, err := p.parseStatement()
		if err != nil {
			return Program{}, err
		}
		statements = append(statements, statement)
	}
	eof := p.current()
	start := eof.Span.Start
	if len(statements) > 0 {
		start = statements[0].Span.Start
	}
	return Program{
		Statements: statements,
		Span:       Span{Start: start, End: eof.Span.End},
	}, nil
}

func (p *parser) parseStatement() (Stmt, error) {
	if p.current().Kind == TokenRParen {
		return Stmt{}, languageError(StageParse, CodeUnexpectedToken, p.current().Span.Start, "unexpected closing parenthesis")
	}
	if p.current().Kind == TokenLParen && p.peekKind(1) == TokenLet {
		open := p.advance()
		p.advance()
		name, err := p.expect(TokenIdentifier)
		if err != nil {
			return Stmt{}, err
		}
		expr, err := p.parseExpression()
		if err != nil {
			return Stmt{}, err
		}
		close, err := p.expect(TokenRParen)
		if err != nil {
			return Stmt{}, err
		}
		return Stmt{
			Kind: StmtLet, Name: name.Lexeme, NameSpan: name.Span, Expr: expr,
			Span: Span{Start: open.Span.Start, End: close.Span.End},
		}, nil
	}
	if p.current().Kind == TokenLParen && p.peekKind(1) == TokenPrint {
		open := p.advance()
		p.advance()
		expr, err := p.parseExpression()
		if err != nil {
			return Stmt{}, err
		}
		close, err := p.expect(TokenRParen)
		if err != nil {
			return Stmt{}, err
		}
		return Stmt{
			Kind: StmtPrint, Expr: expr,
			Span: Span{Start: open.Span.Start, End: close.Span.End},
		}, nil
	}
	expr, err := p.parseExpression()
	if err != nil {
		return Stmt{}, err
	}
	return Stmt{Kind: StmtExpr, Expr: expr, Span: expr.Span}, nil
}

func (p *parser) parseExpression() (*Expr, error) {
	token := p.current()
	switch token.Kind {
	case TokenInteger:
		p.advance()
		return &Expr{Kind: ExprInteger, Integer: token.Integer, Span: token.Span}, nil
	case TokenIdentifier:
		p.advance()
		return &Expr{Kind: ExprName, Name: token.Lexeme, Span: token.Span}, nil
	case TokenLParen:
		open := p.advance()
		op := p.current()
		if !isBinaryOperator(op.Kind) {
			if op.Kind == TokenEOF || op.Kind == TokenRParen {
				return nil, languageError(StageParse, CodeExpectedExpression, op.Span.Start, "expected binary expression")
			}
			return nil, languageError(StageParse, CodeUnexpectedToken, op.Span.Start, "expected binary operator")
		}
		p.advance()
		left, err := p.parseExpression()
		if err != nil {
			return nil, err
		}
		right, err := p.parseExpression()
		if err != nil {
			return nil, err
		}
		close, err := p.expect(TokenRParen)
		if err != nil {
			return nil, err
		}
		return &Expr{
			Kind: ExprBinary, Op: op.Kind, Left: left, Right: right,
			Span: Span{Start: open.Span.Start, End: close.Span.End},
		}, nil
	case TokenEOF, TokenRParen:
		return nil, languageError(StageParse, CodeExpectedExpression, token.Span.Start, "expected expression")
	default:
		return nil, languageError(StageParse, CodeUnexpectedToken, token.Span.Start, "unexpected token in expression")
	}
}

func (p *parser) current() Token {
	return p.tokens[p.index]
}

func (p *parser) peekKind(distance int) TokenKind {
	index := p.index + distance
	if index < 0 || index >= len(p.tokens) {
		return TokenInvalid
	}
	return p.tokens[index].Kind
}

func (p *parser) advance() Token {
	token := p.current()
	if p.index < len(p.tokens)-1 {
		p.index++
	}
	return token
}

func (p *parser) expect(kind TokenKind) (Token, error) {
	token := p.current()
	if token.Kind != kind {
		return Token{}, languageError(StageParse, CodeExpectedToken, token.Span.Start, "required token is missing")
	}
	p.advance()
	return token, nil
}

func validateTokenStream(tokens []Token) error {
	defaultPos := Position{Line: 1, Column: 1}
	if len(tokens) == 0 {
		return languageError(StageParse, CodeInvalidTokenStream, defaultPos, "token stream must end in EOF")
	}
	previousEnd := Position{Offset: 0, Line: 1, Column: 1}
	for i, token := range tokens {
		pos := token.Span.Start
		if !validPosition(pos) {
			pos = defaultPos
		}
		if !validSpan(token.Span) || !possibleIgnoredGap(previousEnd, token.Span.Start) {
			return languageError(StageParse, CodeInvalidTokenStream, pos, "token spans are invalid or unordered")
		}
		if token.Kind == TokenEOF {
			if i != len(tokens)-1 || token.Lexeme != "" || token.Integer != 0 || token.Span.Start != token.Span.End {
				return languageError(StageParse, CodeInvalidTokenStream, pos, "EOF must be the final empty token")
			}
			previousEnd = token.Span.End
			continue
		}
		if i == len(tokens)-1 {
			return languageError(StageParse, CodeInvalidTokenStream, pos, "token stream is missing EOF")
		}
		if token.Span.End.Offset-token.Span.Start.Offset != len(token.Lexeme) || token.Lexeme == "" ||
			token.Span.End.Line != token.Span.Start.Line || token.Span.End.Column-token.Span.Start.Column != len(token.Lexeme) {
			return languageError(StageParse, CodeInvalidTokenStream, pos, "token lexeme and span disagree")
		}
		if !validTokenPayload(token) {
			return languageError(StageParse, CodeInvalidTokenStream, pos, "token payload is invalid")
		}
		previousEnd = token.Span.End
	}
	if tokens[len(tokens)-1].Kind != TokenEOF {
		return languageError(StageParse, CodeInvalidTokenStream, tokens[len(tokens)-1].Span.Start, "token stream is missing EOF")
	}
	return nil
}

func possibleIgnoredGap(previous, next Position) bool {
	return possiblePositionAdvance(previous, next)
}

func validTokenPayload(token Token) bool {
	if token.Kind != TokenInteger && token.Integer != 0 {
		return false
	}
	switch token.Kind {
	case TokenLParen:
		return token.Lexeme == "("
	case TokenRParen:
		return token.Lexeme == ")"
	case TokenPlus:
		return token.Lexeme == "+"
	case TokenMinus:
		return token.Lexeme == "-"
	case TokenStar:
		return token.Lexeme == "*"
	case TokenSlash:
		return token.Lexeme == "/"
	case TokenLet:
		return token.Lexeme == "let"
	case TokenPrint:
		return token.Lexeme == "print"
	case TokenIdentifier:
		return validIdentifier(token.Lexeme) && token.Lexeme != "let" && token.Lexeme != "print"
	case TokenInteger:
		if !allDigits(token.Lexeme) {
			return false
		}
		value, err := strconv.ParseInt(token.Lexeme, 10, 64)
		return err == nil && value == token.Integer
	default:
		return false
	}
}

func allDigits(text string) bool {
	if text == "" {
		return false
	}
	for i := 0; i < len(text); i++ {
		if !isDigit(text[i]) {
			return false
		}
	}
	return true
}

func validIdentifier(text string) bool {
	if text == "" || !isIdentifierStart(text[0]) {
		return false
	}
	for i := 1; i < len(text); i++ {
		if !isIdentifierContinue(text[i]) {
			return false
		}
	}
	return true
}

func isBinaryOperator(kind TokenKind) bool {
	return kind == TokenPlus || kind == TokenMinus || kind == TokenStar || kind == TokenSlash
}
