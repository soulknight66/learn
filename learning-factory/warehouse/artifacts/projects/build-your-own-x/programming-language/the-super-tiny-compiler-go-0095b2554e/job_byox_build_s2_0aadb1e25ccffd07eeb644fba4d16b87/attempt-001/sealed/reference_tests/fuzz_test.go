package reference_tests

import (
	"bytes"
	"testing"

	pf "example.com/prefixforge"
)

func FuzzPipelineNeverPanics(f *testing.F) {
	for _, seed := range []string{"1", "()", `(add 1 2)`, `"x\\n"`, `(if true 1 2)`, string([]byte{0xff})} {
		f.Add(seed)
	}
	f.Fuzz(func(t *testing.T, source string) {
		tokens, err := pf.Tokenize(source)
		if err != nil {
			return
		}
		program, err := pf.Parse(tokens)
		if err != nil {
			return
		}
		code, err := pf.Compile(program)
		if err != nil {
			return
		}
		_, _ = pf.Evaluate(program, nil)
		_, _ = pf.Run(code, nil)
	})
}

func FuzzValidProgramsAgree(f *testing.F) {
	for _, seed := range []string{"1", `(add 1 2)`, `(and false (eq (div 1 0) 0))`, `(print "x") 2`} {
		f.Add(seed)
	}
	f.Fuzz(func(t *testing.T, source string) {
		tokens, err := pf.Tokenize(source)
		if err != nil {
			return
		}
		program, err := pf.Parse(tokens)
		if err != nil {
			return
		}
		code, err := pf.Compile(program)
		if err != nil {
			return
		}
		var evalOut, vmOut bytes.Buffer
		evalValue, evalErr := pf.Evaluate(program, &evalOut)
		vmValue, vmErr := pf.Run(code, &vmOut)
		if (evalErr == nil) != (vmErr == nil) {
			t.Fatalf("error disagreement: eval=%v vm=%v", evalErr, vmErr)
		}
		if evalErr == nil && evalValue != vmValue {
			t.Fatalf("value disagreement: eval=%#v vm=%#v", evalValue, vmValue)
		}
		if evalOut.String() != vmOut.String() {
			t.Fatalf("output disagreement: eval=%q vm=%q", evalOut.String(), vmOut.String())
		}
	})
}
