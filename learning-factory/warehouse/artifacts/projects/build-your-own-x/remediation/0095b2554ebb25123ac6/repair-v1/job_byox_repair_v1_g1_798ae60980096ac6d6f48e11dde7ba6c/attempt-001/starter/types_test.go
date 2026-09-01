package pebble

import (
	"errors"
	"testing"
)

func TestStarterErrorContract(t *testing.T) {
	err := error(&Error{
		Stage:   StageScan,
		Code:    CodeInvalidChar,
		Pos:     Position{Offset: 4, Line: 2, Column: 1},
		Message: "unexpected source byte",
	})
	var languageErr *Error
	if !errors.As(err, &languageErr) {
		t.Fatalf("error type = %T, want *Error", err)
	}
	if languageErr.Stage != StageScan || languageErr.Code != CodeInvalidChar ||
		languageErr.Pos != (Position{Offset: 4, Line: 2, Column: 1}) {
		t.Fatalf("structured error = %#v", languageErr)
	}
	if got := languageErr.Error(); got != "SCAN/INVALID_CHAR at 2:1: unexpected source byte" {
		t.Fatalf("Error() = %q", got)
	}
}

func TestEnumZeroValuesAreInvalid(t *testing.T) {
	if TokenKind(0) != TokenInvalid || ExprKind(0) != ExprInvalid || StmtKind(0) != StmtInvalid || OpCode(0) != OpInvalid {
		t.Fatal("zero values must remain invalid sentinels")
	}
}
