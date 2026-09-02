// Package prefixforge defines the public surface of the Prefix Forge compiler.
package prefixforge

import (
	"fmt"
	"strconv"
)

const (
	MaxSourceBytes  = 1 << 20
	MaxNesting      = 256
	MaxInstructions = 100_000
	MaxStackDepth   = 16_384
	MaxSteps        = 1_000_000
)

// Position is a location in the original source. Offsets and columns count bytes.
type Position struct {
	Offset int
	Line   int
	Column int
}

// Span is a half-open source range.
type Span struct {
	Start Position
	End   Position
}

func (s Span) String() string {
	return fmt.Sprintf("%d:%d", s.Start.Line, s.Start.Column)
}

// StageError is returned for every source or bytecode pipeline failure.
type StageError struct {
	Stage   string
	At      Span
	Message string
}

func (e *StageError) Error() string {
	if e == nil {
		return "<nil>"
	}
	return fmt.Sprintf("%s at %s: %s", e.Stage, e.At, e.Message)
}

type TokenKind string

const (
	TokenLParen     TokenKind = "LPAREN"
	TokenRParen     TokenKind = "RPAREN"
	TokenNumber     TokenKind = "NUMBER"
	TokenString     TokenKind = "STRING"
	TokenIdentifier TokenKind = "IDENTIFIER"
	TokenEOF        TokenKind = "EOF"
)

type Token struct {
	Kind    TokenKind
	Lexeme  string
	Literal string
	At      Span
}

type Expr interface {
	SourceSpan() Span
	exprNode()
}

type NumberExpr struct {
	At    Span
	Value int64
}

func (e NumberExpr) SourceSpan() Span { return e.At }
func (NumberExpr) exprNode()           {}

type StringExpr struct {
	At    Span
	Value string
}

func (e StringExpr) SourceSpan() Span { return e.At }
func (StringExpr) exprNode()           {}

type BoolExpr struct {
	At    Span
	Value bool
}

func (e BoolExpr) SourceSpan() Span { return e.At }
func (BoolExpr) exprNode()           {}

type CallExpr struct {
	At       Span
	Name     string
	NameSpan Span
	Args     []Expr
}

func (e CallExpr) SourceSpan() Span { return e.At }
func (CallExpr) exprNode()           {}

type Program struct {
	At    Span
	Exprs []Expr
}

type ValueType string

const (
	TypeNumber  ValueType = "number"
	TypeString  ValueType = "string"
	TypeBoolean ValueType = "boolean"
)

type Value struct {
	Kind    ValueType
	Number  int64
	Text    string
	Boolean bool
}

func NumberValue(n int64) Value { return Value{Kind: TypeNumber, Number: n} }
func StringValue(s string) Value { return Value{Kind: TypeString, Text: s} }
func BoolValue(b bool) Value     { return Value{Kind: TypeBoolean, Boolean: b} }

func (v Value) String() string {
	switch v.Kind {
	case TypeNumber:
		return strconv.FormatInt(v.Number, 10)
	case TypeString:
		return v.Text
	case TypeBoolean:
		return strconv.FormatBool(v.Boolean)
	default:
		return "<invalid>"
	}
}
