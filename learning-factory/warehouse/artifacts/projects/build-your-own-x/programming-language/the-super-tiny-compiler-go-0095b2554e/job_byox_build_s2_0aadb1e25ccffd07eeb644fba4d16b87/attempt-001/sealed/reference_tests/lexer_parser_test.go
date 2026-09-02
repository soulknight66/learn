package reference_tests

import (
	"errors"
	"strings"
	"testing"

	pf "example.com/prefixforge"
)

func TestLexerKindsLiteralsAndBytePositions(t *testing.T) {
	source := "; λ comment\n(concat \"x\\t\" \"λ\")"
	tokens, err := pf.Tokenize(source)
	if err != nil {
		t.Fatal(err)
	}
	want := []pf.TokenKind{pf.TokenLParen, pf.TokenIdentifier, pf.TokenString, pf.TokenString, pf.TokenRParen, pf.TokenEOF}
	if len(tokens) != len(want) {
		t.Fatalf("tokens = %#v", tokens)
	}
	for i := range want {
		if tokens[i].Kind != want[i] {
			t.Errorf("token %d = %s, want %s", i, tokens[i].Kind, want[i])
		}
	}
	if tokens[2].Literal != "x\t" || tokens[3].Literal != "λ" {
		t.Errorf("string literals = %q, %q", tokens[2].Literal, tokens[3].Literal)
	}
	if tokens[4].At.Start.Column != 19 {
		t.Errorf("byte column for closing parenthesis = %d", tokens[4].At.Start.Column)
	}
}

func TestLexerFailuresAreLocated(t *testing.T) {
	cases := []struct {
		name   string
		source string
		line   int
		column int
	}{
		{"invalid escape", "\"x\\q\"", 1, 3},
		{"unterminated", "\n\"x", 2, 1},
		{"uppercase", "A", 1, 1},
		{"bare minus", "-", 1, 1},
		{"invalid utf8", string([]byte{0xff}), 1, 1},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := pf.Tokenize(tc.source)
			if err == nil {
				t.Fatal("input succeeded")
			}
			var stage *pf.StageError
			if !errors.As(err, &stage) || stage.Stage != "lex" {
				t.Fatalf("error = %T %v", err, err)
			}
			if stage.At.Start.Line != tc.line || stage.At.Start.Column != tc.column {
				t.Errorf("position = %+v", stage.At.Start)
			}
		})
	}
}

func TestLexerSourceLimit(t *testing.T) {
	if _, err := pf.Tokenize(strings.Repeat(" ", pf.MaxSourceBytes)); err != nil {
		t.Fatalf("exact limit rejected: %v", err)
	}
	if _, err := pf.Tokenize(strings.Repeat(" ", pf.MaxSourceBytes+1)); err == nil {
		t.Fatal("over-limit source accepted")
	}
}

func TestParserBoundsAndTokenProtocol(t *testing.T) {
	accepted := strings.Repeat("(print ", pf.MaxNesting) + "1" + strings.Repeat(")", pf.MaxNesting)
	parseSource(t, accepted)
	rejected := "(print " + accepted + ")"
	tokens, err := pf.Tokenize(rejected)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := pf.Parse(tokens); err == nil {
		t.Fatal("over-nested program accepted")
	}

	if _, err := pf.Parse(nil); err == nil {
		t.Fatal("missing EOF accepted")
	}
	eof := pf.Token{Kind: pf.TokenEOF, At: pf.Span{Start: pf.Position{Line: 1, Column: 1}, End: pf.Position{Line: 1, Column: 1}}}
	if _, err := pf.Parse([]pf.Token{eof, eof}); err == nil {
		t.Fatal("token after EOF accepted")
	}
}

func TestParserRejectsIntegerOutsideInt64(t *testing.T) {
	for _, source := range []string{"9223372036854775808", "-9223372036854775809"} {
		tokens, err := pf.Tokenize(source)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := pf.Parse(tokens); err == nil {
			t.Fatalf("Parse(%q) succeeded", source)
		}
	}
}
