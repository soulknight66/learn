package public_tests

import (
	"bytes"
	"errors"
	"testing"

	pf "example.com/prefixforge"
)

func TestStage3TypeChecking(t *testing.T) {
	program := mustParse(t, `(if (lt 1 2) (concat "a" "b") "c")`)
	types, err := pf.Check(program)
	if err != nil {
		t.Fatalf("Check returned error: %v", err)
	}
	if len(types) != 1 || types[0] != pf.TypeString {
		t.Fatalf("types = %#v", types)
	}

	bad := mustParse(t, `(if 1 "yes" "no")`)
	if _, err := pf.Check(bad); err == nil {
		t.Fatal("number condition was accepted")
	}
}

func TestStage4And5ExecuteExamples(t *testing.T) {
	cases := []struct {
		source string
		want   pf.Value
	}{
		{`(add 7 (mul 3 4))`, pf.NumberValue(19)},
		{`(div -9 2)`, pf.NumberValue(-4)},
		{`(eq (concat "go" "pher") "gopher")`, pf.BoolValue(true)},
		{`(if (lt 9 2) 10 (sub 10 3))`, pf.NumberValue(7)},
	}
	for _, tc := range cases {
		t.Run(tc.source, func(t *testing.T) {
			got, err := pf.Execute(tc.source, nil)
			if err != nil {
				t.Fatalf("Execute returned error: %v", err)
			}
			if got != tc.want {
				t.Fatalf("value = %#v, want %#v", got, tc.want)
			}
		})
	}
}

func TestStage4LazyControlFlow(t *testing.T) {
	var output bytes.Buffer
	value, err := pf.Execute(`(if true (print "chosen") (print "wrong"))`, &output)
	if err != nil {
		t.Fatalf("Execute returned error: %v", err)
	}
	if value != pf.StringValue("chosen") || output.String() != "chosen\n" {
		t.Fatalf("value/output = %#v / %q", value, output.String())
	}

	value, err = pf.Execute(`(and false (eq (div 1 0) 0))`, nil)
	if err != nil {
		t.Fatalf("short-circuited division failed: %v", err)
	}
	if value != pf.BoolValue(false) {
		t.Fatalf("and value = %#v", value)
	}
}

func TestStage5InterpreterAgreesWithVM(t *testing.T) {
	program := mustParse(t, `(print "first") (if (not false) (add 20 22) 0)`)
	var interpreted, compiled bytes.Buffer
	want, err := pf.Evaluate(program, &interpreted)
	if err != nil {
		t.Fatal(err)
	}
	code, err := pf.Compile(program)
	if err != nil {
		t.Fatal(err)
	}
	got, err := pf.Run(code, &compiled)
	if err != nil {
		t.Fatal(err)
	}
	if got != want || compiled.String() != interpreted.String() {
		t.Fatalf("VM = %#v/%q; evaluator = %#v/%q", got, compiled.String(), want, interpreted.String())
	}
}

func TestRuntimeErrorsAreStageErrors(t *testing.T) {
	_, err := pf.Execute(`(div 1 0)`, nil)
	if err == nil {
		t.Fatal("division by zero succeeded")
	}
	var stage *pf.StageError
	if !errors.As(err, &stage) || stage.Stage != "vm" {
		t.Fatalf("error = %T %v", err, err)
	}
}

func mustParse(t *testing.T, source string) pf.Program {
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
