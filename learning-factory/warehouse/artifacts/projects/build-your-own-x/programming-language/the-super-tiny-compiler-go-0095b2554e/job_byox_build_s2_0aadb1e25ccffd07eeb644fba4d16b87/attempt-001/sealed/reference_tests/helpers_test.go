package reference_tests

import (
	"testing"

	pf "example.com/prefixforge"
)

func parseSource(t testing.TB, source string) pf.Program {
	t.Helper()
	tokens, err := pf.Tokenize(source)
	if err != nil {
		t.Fatalf("Tokenize(%q): %v", source, err)
	}
	program, err := pf.Parse(tokens)
	if err != nil {
		t.Fatalf("Parse(%q): %v", source, err)
	}
	return program
}

func compileSource(t testing.TB, source string) pf.Bytecode {
	t.Helper()
	program := parseSource(t, source)
	code, err := pf.Compile(program)
	if err != nil {
		t.Fatalf("Compile(%q): %v", source, err)
	}
	return code
}
