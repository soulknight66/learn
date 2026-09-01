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
	return possiblePositionAdvance(span.Start, span.End)
}

func spanContains(outer, inner Span) bool {
	return validSpan(outer) && validSpan(inner) &&
		positionAtOrBefore(outer.Start, inner.Start) && positionAtOrBefore(inner.End, outer.End)
}

// possiblePositionAdvance reports whether some byte sequence could connect two
// positions. Each line increment consumes one LF byte, and bytes after the
// final LF determine the one-based ending column.
func possiblePositionAdvance(previous, next Position) bool {
	if !validPosition(previous) || !validPosition(next) || next.Offset < previous.Offset || next.Line < previous.Line {
		return false
	}
	offsetDelta := next.Offset - previous.Offset
	lineDelta := next.Line - previous.Line
	if offsetDelta == 0 {
		return previous == next
	}
	if lineDelta == 0 {
		return next.Column-previous.Column == offsetDelta
	}
	return lineDelta+next.Column-1 <= offsetDelta
}

func positionAtOrBefore(first, second Position) bool {
	return possiblePositionAdvance(first, second)
}
