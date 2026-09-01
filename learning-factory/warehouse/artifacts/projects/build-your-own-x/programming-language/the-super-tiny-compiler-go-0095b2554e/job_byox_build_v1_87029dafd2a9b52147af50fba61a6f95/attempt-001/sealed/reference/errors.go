package pebble

import "fmt"

type Stage string

const (
	StageScan     Stage = "SCAN"
	StageParse    Stage = "PARSE"
	StageAnalyze  Stage = "ANALYZE"
	StageCompile  Stage = "COMPILE"
	StageValidate Stage = "VALIDATE"
	StageRun      Stage = "RUN"
)

const (
	CodeNotImplemented     = "NOT_IMPLEMENTED"
	CodeInvalidChar        = "INVALID_CHAR"
	CodeIntegerRange       = "INTEGER_RANGE"
	CodeExpectedExpression = "EXPECTED_EXPRESSION"
	CodeUnexpectedToken    = "UNEXPECTED_TOKEN"
	CodeExpectedToken      = "EXPECTED_TOKEN"
	CodeInvalidTokenStream = "INVALID_TOKEN_STREAM"
	CodeUndefinedName      = "UNDEFINED_NAME"
	CodeRedeclaredName     = "REDECLARED_NAME"
	CodeInvalidAST         = "INVALID_AST"
	CodeInvalidInput       = "INVALID_INPUT"
	CodeInvalidBytecode    = "INVALID_BYTECODE"
	CodeIntegerOverflow    = "INTEGER_OVERFLOW"
	CodeDivisionByZero     = "DIVISION_BY_ZERO"
)

type Error struct {
	Stage   Stage
	Code    string
	Pos     Position
	Message string
}

func (e *Error) Error() string {
	if e == nil {
		return "<nil>"
	}
	return fmt.Sprintf("%s/%s at %d:%d: %s", e.Stage, e.Code, e.Pos.Line, e.Pos.Column, e.Message)
}

func languageError(stage Stage, code string, pos Position, message string) error {
	if !validPosition(pos) {
		pos = Position{Line: 1, Column: 1}
	}
	return &Error{Stage: stage, Code: code, Pos: pos, Message: message}
}

func validPosition(pos Position) bool {
	return pos.Offset >= 0 && pos.Line > 0 && pos.Column > 0
}

func validSpan(span Span) bool {
	if !validPosition(span.Start) || !validPosition(span.End) {
		return false
	}
	if span.End.Offset < span.Start.Offset {
		return false
	}
	if span.End.Line < span.Start.Line {
		return false
	}
	if span.End.Line == span.Start.Line && span.End.Column < span.Start.Column {
		return false
	}
	return true
}

func spanContains(outer, inner Span) bool {
	return validSpan(outer) && validSpan(inner) &&
		outer.Start.Offset <= inner.Start.Offset && inner.End.Offset <= outer.End.Offset
}
