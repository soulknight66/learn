package pebble

import (
	"errors"
	"testing"
)

func TestStarterErrorContract(t *testing.T) {
	_, err := Scan("")
	var languageErr *Error
	if !errors.As(err, &languageErr) {
		t.Fatalf("Scan error type = %T, want *Error", err)
	}
	if languageErr.Stage != StageScan || languageErr.Code != CodeNotImplemented {
		t.Fatalf("Scan error = %#v", languageErr)
	}
}

func TestEnumZeroValuesAreInvalid(t *testing.T) {
	if TokenKind(0) != TokenInvalid || ExprKind(0) != ExprInvalid || StmtKind(0) != StmtInvalid || OpCode(0) != OpInvalid {
		t.Fatal("zero values must remain invalid sentinels")
	}
}
