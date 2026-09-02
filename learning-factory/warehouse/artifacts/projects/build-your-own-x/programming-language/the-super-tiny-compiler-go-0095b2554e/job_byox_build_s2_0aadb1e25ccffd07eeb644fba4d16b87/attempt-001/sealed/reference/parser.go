package prefixforge

import (
	"strconv"
)

type parser struct {
	tokens []Token
	index  int
}

func Parse(tokens []Token) (Program, error) {
	if len(tokens) == 0 {
		return Program{}, stageError("parse", initialSpan(), "token stream has no EOF token")
	}
	for i, tok := range tokens {
		if tok.Kind == TokenEOF && i != len(tokens)-1 {
			return Program{}, stageError("parse", tok.At, "token appears after EOF")
		}
	}
	if tokens[len(tokens)-1].Kind != TokenEOF {
		return Program{}, stageError("parse", tokens[len(tokens)-1].At, "token stream has no final EOF token")
	}

	p := &parser{tokens: tokens}
	if p.peek().Kind == TokenEOF {
		return Program{}, stageError("parse", p.peek().At, "program is empty")
	}
	program := Program{}
	for p.peek().Kind != TokenEOF {
		expr, err := p.parseExpr(0)
		if err != nil {
			return Program{}, err
		}
		program.Exprs = append(program.Exprs, expr)
	}
	program.At = Span{
		Start: program.Exprs[0].SourceSpan().Start,
		End:   program.Exprs[len(program.Exprs)-1].SourceSpan().End,
	}
	return program, nil
}

func (p *parser) parseExpr(depth int) (Expr, error) {
	tok := p.peek()
	switch tok.Kind {
	case TokenNumber:
		p.advance()
		value, err := strconv.ParseInt(tok.Lexeme, 10, 64)
		if err != nil {
			return nil, stageError("parse", tok.At, "integer is outside int64 range")
		}
		return NumberExpr{At: tok.At, Value: value}, nil
	case TokenString:
		p.advance()
		return StringExpr{At: tok.At, Value: tok.Literal}, nil
	case TokenIdentifier:
		p.advance()
		switch tok.Lexeme {
		case "true":
			return BoolExpr{At: tok.At, Value: true}, nil
		case "false":
			return BoolExpr{At: tok.At, Value: false}, nil
		default:
			return nil, stageError("parse", tok.At, "bare identifier %q is not an expression", tok.Lexeme)
		}
	case TokenLParen:
		return p.parseCall(depth)
	case TokenRParen:
		return nil, stageError("parse", tok.At, "unexpected closing parenthesis")
	case TokenEOF:
		return nil, stageError("parse", tok.At, "expected expression before EOF")
	default:
		return nil, stageError("parse", tok.At, "unexpected token kind %q", tok.Kind)
	}
}

func (p *parser) parseCall(depth int) (Expr, error) {
	open := p.advance()
	if depth >= MaxNesting {
		return nil, stageError("parse", open.At, "call nesting exceeds %d", MaxNesting)
	}
	name := p.peek()
	if name.Kind == TokenRParen {
		return nil, stageError("parse", name.At, "empty call has no operator")
	}
	if name.Kind == TokenEOF {
		return nil, stageError("parse", name.At, "unterminated call")
	}
	if name.Kind != TokenIdentifier {
		return nil, stageError("parse", name.At, "call operator must be an identifier")
	}
	p.advance()
	call := CallExpr{Name: name.Lexeme, NameSpan: name.At}

	for {
		tok := p.peek()
		switch tok.Kind {
		case TokenRParen:
			close := p.advance()
			call.At = Span{Start: open.At.Start, End: close.At.End}
			return call, nil
		case TokenEOF:
			return nil, stageError("parse", open.At, "unterminated call %q", call.Name)
		default:
			arg, err := p.parseExpr(depth + 1)
			if err != nil {
				return nil, err
			}
			call.Args = append(call.Args, arg)
		}
	}
}

func (p *parser) peek() Token {
	return p.tokens[p.index]
}

func (p *parser) advance() Token {
	tok := p.tokens[p.index]
	if p.index < len(p.tokens)-1 {
		p.index++
	}
	return tok
}
