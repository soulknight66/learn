// Package pebble defines the public surface of the Pebble compiler challenge.
package pebble

// Position is a byte location in source. Offset is zero-based; line and column
// are one-based.
type Position struct {
	Offset int
	Line   int
	Column int
}

// Span is a half-open source interval [Start, End).
type Span struct {
	Start Position
	End   Position
}

// TokenKind classifies a scanned token.
type TokenKind uint8

const (
	TokenInvalid TokenKind = iota
	TokenEOF
	TokenLParen
	TokenRParen
	TokenInteger
	TokenIdentifier
	TokenLet
	TokenPrint
	TokenPlus
	TokenMinus
	TokenStar
	TokenSlash
)

// Token is one scanner result. Integer is meaningful only for TokenInteger.
type Token struct {
	Kind    TokenKind
	Lexeme  string
	Integer int64
	Span    Span
}

// ExprKind classifies an expression node.
type ExprKind uint8

const (
	ExprInvalid ExprKind = iota
	ExprInteger
	ExprName
	ExprBinary
)

// Expr is a Pebble expression. Integer, Name, or Op/Left/Right is meaningful
// according to Kind.
type Expr struct {
	Kind    ExprKind
	Integer int64
	Name    string
	Op      TokenKind
	Left    *Expr
	Right   *Expr
	Span    Span
}

// StmtKind classifies a top-level statement.
type StmtKind uint8

const (
	StmtInvalid StmtKind = iota
	StmtLet
	StmtPrint
	StmtExpr
)

// Stmt is one top-level form. Name is meaningful for StmtLet.
type Stmt struct {
	Kind     StmtKind
	Name     string
	NameSpan Span
	Expr     *Expr
	Span     Span
}

// Program is an ordered collection of statements.
type Program struct {
	Statements []Stmt
	Span       Span
}

// Analysis is the deterministic name-to-local-slot result.
type Analysis struct {
	Slots     map[string]int
	SlotCount int
}

// OpCode is one Pebble virtual-machine operation.
type OpCode uint8

const (
	OpInvalid OpCode = iota
	OpPush
	OpLoad
	OpStore
	OpAdd
	OpSub
	OpMul
	OpDiv
	OpPrint
	OpPop
	OpHalt
)

// Instruction is one bytecode operation and its source origin.
type Instruction struct {
	Op      OpCode
	Operand int64
	Span    Span
}

// Bytecode is an immutable-by-convention compiled program.
type Bytecode struct {
	Instructions []Instruction
	SlotCount    int
}
