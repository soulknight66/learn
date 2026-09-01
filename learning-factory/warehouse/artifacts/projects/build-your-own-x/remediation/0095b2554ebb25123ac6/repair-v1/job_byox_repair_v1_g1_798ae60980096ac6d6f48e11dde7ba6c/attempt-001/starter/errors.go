package pebble

import "fmt"

// Stage identifies the pipeline stage that rejected an input.
type Stage string

const (
	StageScan     Stage = "SCAN"
	StageParse    Stage = "PARSE"
	StageAnalyze  Stage = "ANALYZE"
	StageCompile  Stage = "COMPILE"
	StageValidate Stage = "VALIDATE"
	StageRun      Stage = "RUN"
)

// Stable machine-readable error codes.
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

// Error is the structured failure returned by every compiler stage.
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

func notImplemented(stage Stage) error {
	return &Error{
		Stage:   stage,
		Code:    CodeNotImplemented,
		Pos:     Position{Offset: 0, Line: 1, Column: 1},
		Message: "complete this challenge stage",
	}
}
