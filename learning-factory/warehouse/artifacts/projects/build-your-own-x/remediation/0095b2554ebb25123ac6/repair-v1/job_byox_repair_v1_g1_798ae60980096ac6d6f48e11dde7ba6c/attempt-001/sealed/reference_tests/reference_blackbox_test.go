package referencetests_test

import (
	"errors"
	"reflect"
	"testing"

	pebble "example.com/pebble-reference"
)

func assertError(t *testing.T, err error, stage pebble.Stage, code string) *pebble.Error {
	t.Helper()
	var got *pebble.Error
	if !errors.As(err, &got) {
		t.Fatalf("error = %T %v, want *Error", err, err)
	}
	if got.Stage != stage || got.Code != code {
		t.Fatalf("error = %#v, want %s/%s", got, stage, code)
	}
	return got
}

func TestPipelineStagesAgree(t *testing.T) {
	source := "(let base 10) (let answer (+ (* base 4) 2)) (print answer)"
	tokens, err := pebble.Scan(source)
	if err != nil {
		t.Fatal(err)
	}
	program, err := pebble.Parse(tokens)
	if err != nil {
		t.Fatal(err)
	}
	analysis, err := pebble.Analyze(program)
	if err != nil {
		t.Fatal(err)
	}
	code, err := pebble.Compile(program, analysis)
	if err != nil {
		t.Fatal(err)
	}
	if err := pebble.ValidateBytecode(code); err != nil {
		t.Fatal(err)
	}
	output, err := pebble.Run(code)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(output, []int64{42}) {
		t.Fatalf("output = %#v", output)
	}
	direct, err := pebble.Execute(source)
	if err != nil || !reflect.DeepEqual(direct, output) {
		t.Fatalf("Execute = %#v, %v", direct, err)
	}
}

func TestForgedTokenStreamsAreRejected(t *testing.T) {
	pos := pebble.Position{Line: 1, Column: 1}
	end := pebble.Position{Offset: 1, Line: 1, Column: 2}
	tests := []struct {
		name   string
		tokens []pebble.Token
	}{
		{"empty stream", nil},
		{"missing EOF", []pebble.Token{{Kind: pebble.TokenInteger, Lexeme: "1", Integer: 1, Span: pebble.Span{Start: pos, End: end}}}},
		{"duplicate EOF", []pebble.Token{{Kind: pebble.TokenEOF, Span: pebble.Span{Start: pos, End: pos}}, {Kind: pebble.TokenEOF, Span: pebble.Span{Start: pos, End: pos}}}},
		{"keyword payload mismatch", []pebble.Token{{Kind: pebble.TokenLet, Lexeme: "other", Span: pebble.Span{Start: pos, End: end}}, {Kind: pebble.TokenEOF, Span: pebble.Span{Start: end, End: end}}}},
		{"unknown token kind", []pebble.Token{{Kind: pebble.TokenKind(255), Lexeme: "x", Span: pebble.Span{Start: pos, End: end}}, {Kind: pebble.TokenEOF, Span: pebble.Span{Start: end, End: end}}}},
		{"backward span", []pebble.Token{
			{Kind: pebble.TokenInteger, Lexeme: "1", Integer: 1, Span: pebble.Span{Start: pebble.Position{Offset: 1, Line: 1, Column: 2}, End: pebble.Position{Offset: 2, Line: 1, Column: 3}}},
			{Kind: pebble.TokenEOF, Span: pebble.Span{Start: end, End: end}},
		}},
		{"impossible column after newline", []pebble.Token{
			{Kind: pebble.TokenInteger, Lexeme: "1", Integer: 1, Span: pebble.Span{Start: pebble.Position{Offset: 1, Line: 2, Column: 99}, End: pebble.Position{Offset: 2, Line: 2, Column: 100}}},
			{Kind: pebble.TokenEOF, Span: pebble.Span{Start: pebble.Position{Offset: 2, Line: 2, Column: 100}, End: pebble.Position{Offset: 2, Line: 2, Column: 100}}},
		}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			if _, err := pebble.Parse(test.tokens); err == nil {
				t.Error("error = nil")
			} else {
				assertError(t, err, pebble.StageParse, pebble.CodeInvalidTokenStream)
			}
		})
	}
}

func TestCallerConstructedASTAndAnalysisAreRejected(t *testing.T) {
	tokens, _ := pebble.Scan("(let x 1) (print x)")
	program, _ := pebble.Parse(tokens)
	broken := program
	broken.Statements = append([]pebble.Stmt(nil), program.Statements...)
	broken.Statements[1].Expr = nil
	_, err := pebble.Analyze(broken)
	assertError(t, err, pebble.StageAnalyze, pebble.CodeInvalidAST)

	analysis, _ := pebble.Analyze(program)
	tampered := &pebble.Analysis{Slots: map[string]int{"x": 4}, SlotCount: analysis.SlotCount}
	_, err = pebble.Compile(program, tampered)
	assertError(t, err, pebble.StageCompile, pebble.CodeInvalidInput)

	cycleTokens, _ := pebble.Scan("(+ 1 2)")
	cyclic, _ := pebble.Parse(cycleTokens)
	root := cyclic.Statements[0].Expr
	root.Left = root
	_, err = pebble.Analyze(cyclic)
	assertError(t, err, pebble.StageAnalyze, pebble.CodeInvalidAST)
}

func TestFailureDoesNotExposePartialOutput(t *testing.T) {
	output, err := pebble.Execute("(print 7) (print (/ 8 0))")
	if output != nil {
		t.Fatalf("output = %#v, want nil", output)
	}
	assertError(t, err, pebble.StageRun, pebble.CodeDivisionByZero)
}

func TestSuccessfulNoOutputIsNonNil(t *testing.T) {
	output, err := pebble.Execute("(let x 1) (+ x 2)")
	if err != nil {
		t.Fatal(err)
	}
	if output == nil || len(output) != 0 {
		t.Fatalf("output = %#v", output)
	}
}
