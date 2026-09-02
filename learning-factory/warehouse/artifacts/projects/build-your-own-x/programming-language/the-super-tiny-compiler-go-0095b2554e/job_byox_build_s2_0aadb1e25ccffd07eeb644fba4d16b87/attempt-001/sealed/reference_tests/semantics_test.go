package reference_tests

import (
	"bytes"
	"errors"
	"io"
	"math"
	"strings"
	"testing"

	pf "example.com/prefixforge"
)

func TestEveryBuiltin(t *testing.T) {
	cases := []struct {
		source string
		want   pf.Value
	}{
		{"(add 2 3)", pf.NumberValue(5)},
		{"(sub 2 3)", pf.NumberValue(-1)},
		{"(mul -4 3)", pf.NumberValue(-12)},
		{"(div -9 2)", pf.NumberValue(-4)},
		{"(lt 2 3)", pf.BoolValue(true)},
		{"(eq 2 2)", pf.BoolValue(true)},
		{"(eq \"x\" \"y\")", pf.BoolValue(false)},
		{"(and true false)", pf.BoolValue(false)},
		{"(or false true)", pf.BoolValue(true)},
		{"(not false)", pf.BoolValue(true)},
		{"(concat \"a\" \"b\")", pf.StringValue("ab")},
		{"(if true \"yes\" \"no\")", pf.StringValue("yes")},
	}
	for _, tc := range cases {
		t.Run(tc.source, func(t *testing.T) {
			got, err := pf.Execute(tc.source, nil)
			if err != nil {
				t.Fatal(err)
			}
			if got != tc.want {
				t.Fatalf("got %#v, want %#v", got, tc.want)
			}
		})
	}
}

func TestEffectsOrderAndLazyBranches(t *testing.T) {
	source := `(print "one") (if false (print "wrong") (print "two")) (and false (eq (div 1 0) 0))`
	var out bytes.Buffer
	value, err := pf.Execute(source, &out)
	if err != nil {
		t.Fatal(err)
	}
	if value != pf.BoolValue(false) || out.String() != "one\ntwo\n" {
		t.Fatalf("value/output = %#v / %q", value, out.String())
	}
}

func TestCheckerRejectsInvalidPrograms(t *testing.T) {
	sources := []string{
		"(missing 1)",
		"(add 1)",
		"(add 1 true)",
		"(eq 1 \"1\")",
		"(if true 1 \"one\")",
		"(not 0)",
	}
	for _, source := range sources {
		t.Run(source, func(t *testing.T) {
			program := parseSource(t, source)
			_, err := pf.Check(program)
			if err == nil {
				t.Fatal("Check succeeded")
			}
			var stage *pf.StageError
			if !errors.As(err, &stage) || stage.Stage != "check" {
				t.Fatalf("error = %T %v", err, err)
			}
		})
	}
}

func TestCheckedArithmeticFailuresAgree(t *testing.T) {
	sources := []string{
		"(div 1 0)",
		"(div -9223372036854775808 -1)",
		"(add 9223372036854775807 1)",
		"(sub -9223372036854775808 1)",
		"(mul 9223372036854775807 2)",
	}
	for _, source := range sources {
		t.Run(source, func(t *testing.T) {
			program := parseSource(t, source)
			if _, err := pf.Evaluate(program, nil); err == nil {
				t.Fatal("evaluator succeeded")
			}
			if _, err := pf.Run(compileSource(t, source), nil); err == nil {
				t.Fatal("VM succeeded")
			}
		})
	}
	value, err := pf.Execute("(add 9223372036854775807 0)", nil)
	if err != nil || value.Number != math.MaxInt64 {
		t.Fatalf("boundary add = %#v, %v", value, err)
	}
}

type failingWriter struct{}

func (failingWriter) Write([]byte) (int, error) { return 0, io.ErrClosedPipe }

func TestWriterFailuresPropagate(t *testing.T) {
	program := parseSource(t, `(print "x")`)
	for name, run := range map[string]func() error{
		"evaluator": func() error { _, err := pf.Evaluate(program, failingWriter{}); return err },
		"vm":        func() error { _, err := pf.Run(compileSource(t, `(print "x")`), failingWriter{}); return err },
	} {
		t.Run(name, func(t *testing.T) {
			if err := run(); err == nil || !strings.Contains(err.Error(), "write") {
				t.Fatalf("error = %v", err)
			}
		})
	}
}

func TestCompilerRecordsStackAndHalt(t *testing.T) {
	code := compileSource(t, `(add 1 (mul 2 3))`)
	if code.MaxStack != 3 {
		t.Errorf("MaxStack = %d, want 3", code.MaxStack)
	}
	if len(code.Code) == 0 || code.Code[len(code.Code)-1].Op != pf.OpHalt {
		t.Fatal("bytecode does not end in HALT")
	}
	if got := code.String(); !strings.HasPrefix(got, "0000 PUSH_NUMBER") || strings.Count(got, "\n") != len(code.Code) {
		t.Fatalf("unstable disassembly: %q", got)
	}
}
