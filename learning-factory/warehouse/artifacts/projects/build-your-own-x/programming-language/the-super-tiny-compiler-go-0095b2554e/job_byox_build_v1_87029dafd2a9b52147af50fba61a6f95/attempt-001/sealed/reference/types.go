// Package pebble implements the sealed reference for the Pebble challenge.
package pebble

type Position struct {
	Offset int
	Line   int
	Column int
}

type Span struct {
	Start Position
	End   Position
}

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

type Token struct {
	Kind    TokenKind
	Lexeme  string
	Integer int64
	Span    Span
}

type ExprKind uint8

const (
	ExprInvalid ExprKind = iota
	ExprInteger
	ExprName
	ExprBinary
)

type Expr struct {
	Kind    ExprKind
	Integer int64
	Name    string
	Op      TokenKind
	Left    *Expr
	Right   *Expr
	Span    Span
}

type StmtKind uint8

const (
	StmtInvalid StmtKind = iota
	StmtLet
	StmtPrint
	StmtExpr
)

type Stmt struct {
	Kind     StmtKind
	Name     string
	NameSpan Span
	Expr     *Expr
	Span     Span
}

type Program struct {
	Statements []Stmt
	Span       Span
}

type Analysis struct {
	Slots     map[string]int
	SlotCount int
}

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

type Instruction struct {
	Op      OpCode
	Operand int64
	Span    Span
}

type Bytecode struct {
	Instructions []Instruction
	SlotCount    int
}
