package public_tests

import (
	"errors"
	"testing"

	pf "example.com/prefixforge"
)

func TestStage1TokenizeSpansAndEscapes(t *testing.T) {
	tokens, err := pf.Tokenize("; ignored\n(add -12 \"a\\nλ\")")
	if err != nil {
		t.Fatalf("Tokenize returned error: %v", err)
	}
	wantKinds := []pf.TokenKind{
		pf.TokenLParen, pf.TokenIdentifier, pf.TokenNumber,
		pf.TokenString, pf.TokenRParen, pf.TokenEOF,
	}
	if len(tokens) != len(wantKinds) {
		t.Fatalf("got %d tokens, want %d: %#v", len(tokens), len(wantKinds), tokens)
	}
	for i, want := range wantKinds {
		if tokens[i].Kind != want {
			t.Errorf("token %d kind = %s, want %s", i, tokens[i].Kind, want)
		}
	}
	if got := tokens[3].Literal; got != "a\nλ" {
		t.Errorf("unescaped string = %q", got)
	}
	if got := tokens[0].At.Start; got.Line != 2 || got.Column != 1 || got.Offset != 10 {
		t.Errorf("opening parenthesis starts at %+v", got)
	}
	if tokens[len(tokens)-1].At.Start != tokens[len(tokens)-1].At.End {
		t.Errorf("EOF span is not zero-width: %+v", tokens[len(tokens)-1].At)
	}
}

func TestStage1LexicalFailureIsLocated(t *testing.T) {
	_, err := pf.Tokenize("\n\"bad\\q\"")
	if err == nil {
		t.Fatal("invalid escape was accepted")
	}
	var stage *pf.StageError
	if !errors.As(err, &stage) {
		t.Fatalf("error type = %T, want *StageError", err)
	}
	if stage.Stage != "lex" || stage.At.Start.Line != 2 {
		t.Errorf("unexpected located error: %+v", stage)
	}
}

func TestStage2ParseNestedCall(t *testing.T) {
	tokens, err := pf.Tokenize("(add 1 (mul 2 3))")
	if err != nil {
		t.Fatal(err)
	}
	program, err := pf.Parse(tokens)
	if err != nil {
		t.Fatalf("Parse returned error: %v", err)
	}
	if len(program.Exprs) != 1 {
		t.Fatalf("expression count = %d", len(program.Exprs))
	}
	outer, ok := program.Exprs[0].(pf.CallExpr)
	if !ok {
		t.Fatalf("root type = %T, want CallExpr", program.Exprs[0])
	}
	if outer.Name != "add" || len(outer.Args) != 2 {
		t.Fatalf("outer call = %#v", outer)
	}
	inner, ok := outer.Args[1].(pf.CallExpr)
	if !ok || inner.Name != "mul" || len(inner.Args) != 2 {
		t.Fatalf("inner call = %#v", outer.Args[1])
	}
}

func TestStage2RejectsMalformedCalls(t *testing.T) {
	for _, source := range []string{"", "()", "(1 2)", ")", "(add 1 2"} {
		t.Run(source, func(t *testing.T) {
			tokens, lexErr := pf.Tokenize(source)
			if lexErr != nil {
				t.Fatalf("setup lex error: %v", lexErr)
			}
			if _, err := pf.Parse(tokens); err == nil {
				t.Fatalf("Parse(%q) succeeded", source)
			}
		})
	}
}
