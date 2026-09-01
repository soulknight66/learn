package pebble

import (
	"errors"
	"math"
	"reflect"
	"sync"
	"testing"
)

func requireError(t *testing.T, err error, stage Stage, code string, line, column int) {
	t.Helper()
	var got *Error
	if !errors.As(err, &got) {
		t.Fatalf("error = %T %v, want *Error", err, err)
	}
	if got.Stage != stage || got.Code != code || got.Pos.Line != line || got.Pos.Column != column {
		t.Fatalf("error = %#v, want %s/%s at %d:%d", got, stage, code, line, column)
	}
}

func TestScannerProducesPositionedEOF(t *testing.T) {
	tokens, err := Scan("# c\r\n(let x 0)")
	if err != nil {
		t.Fatal(err)
	}
	if len(tokens) != 6 {
		t.Fatalf("tokens = %#v", tokens)
	}
	if got := tokens[0].Span.Start; got != (Position{Offset: 5, Line: 2, Column: 1}) {
		t.Fatalf("first position = %#v", got)
	}
	if tokens[3].Integer != 0 || tokens[3].Lexeme != "0" {
		t.Fatalf("integer token = %#v", tokens[3])
	}
	eof := tokens[len(tokens)-1]
	if eof.Kind != TokenEOF || eof.Span.Start != eof.Span.End || eof.Span.Start.Offset != len("# c\r\n(let x 0)") {
		t.Fatalf("EOF = %#v", eof)
	}
}

func TestEndToEndPrograms(t *testing.T) {
	tests := []struct {
		name   string
		source string
		want   []int64
	}{
		{"empty", "# only a comment", []int64{}},
		{"precedence is structural", "(print (+ 2 (* 3 4)))", []int64{14}},
		{"ordered names", "(let x 8) (let y (- x 3)) (print (/ (* y x) 2))", []int64{20}},
		{"negative division", "(print (/ (- 0 7) 3))", []int64{-2}},
		{"discard expression", "(+ 4 5) (print 6)", []int64{6}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			got, err := Execute(test.source)
			if err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(got, test.want) {
				t.Fatalf("output = %#v, want %#v", got, test.want)
			}
		})
	}
}

func TestAnalysisErrorOrderAndSlots(t *testing.T) {
	tokens, _ := Scan("(let first 1) (let second first) (print second)")
	program, _ := Parse(tokens)
	analysis, err := Analyze(program)
	if err != nil {
		t.Fatal(err)
	}
	if analysis.SlotCount != 2 || analysis.Slots["first"] != 0 || analysis.Slots["second"] != 1 {
		t.Fatalf("analysis = %#v", analysis)
	}

	tokens, _ = Scan("(let x 1) (let x missing)")
	program, _ = Parse(tokens)
	_, err = Analyze(program)
	requireError(t, err, StageAnalyze, CodeRedeclaredName, 1, 16)
}

func TestBuildIsDeterministic(t *testing.T) {
	source := "(let a 2) (let b 3) (print (* (+ a b) b))"
	first, err := Build(source)
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 20; i++ {
		next, err := Build(source)
		if err != nil {
			t.Fatal(err)
		}
		if !reflect.DeepEqual(first, next) {
			t.Fatalf("build %d differs", i)
		}
	}
}

func TestCheckedArithmetic(t *testing.T) {
	tests := []struct {
		source string
		code   string
	}{
		{"(print (+ 9223372036854775807 1))", CodeIntegerOverflow},
		{"(print (- (- 0 9223372036854775807) 2))", CodeIntegerOverflow},
		{"(print (* 9223372036854775807 2))", CodeIntegerOverflow},
		{"(print (/ 1 0))", CodeDivisionByZero},
		{"(print (/ (- (- 0 9223372036854775807) 1) (- 0 1)))", CodeIntegerOverflow},
	}
	for _, test := range tests {
		output, err := Execute(test.source)
		if output != nil {
			t.Fatalf("output = %#v for %q", output, test.source)
		}
		var got *Error
		if !errors.As(err, &got) || got.Stage != StageRun || got.Code != test.code {
			t.Fatalf("error = %#v for %q", err, test.source)
		}
	}
}

func TestValidatorAndRunDoNotMutateInput(t *testing.T) {
	span := Span{Start: Position{Line: 1, Column: 1}, End: Position{Offset: 1, Line: 1, Column: 2}}
	code := Bytecode{Instructions: []Instruction{
		{Op: OpPush, Operand: math.MaxInt64, Span: span},
		{Op: OpPrint, Span: span},
		{Op: OpHalt, Span: span},
	}}
	want := Bytecode{Instructions: append([]Instruction(nil), code.Instructions...)}
	if output, err := Run(code); err != nil || !reflect.DeepEqual(output, []int64{math.MaxInt64}) {
		t.Fatalf("Run = %#v, %v", output, err)
	}
	if !reflect.DeepEqual(code, want) {
		t.Fatalf("Run mutated bytecode: %#v", code)
	}
}

func TestConcurrentRunsHaveFreshState(t *testing.T) {
	code, err := Build("(let x 21) (print (* x 2))")
	if err != nil {
		t.Fatal(err)
	}
	const workers = 16
	errorsFound := make(chan error, workers)
	var group sync.WaitGroup
	for i := 0; i < workers; i++ {
		group.Add(1)
		go func() {
			defer group.Done()
			output, err := Run(code)
			if err != nil {
				errorsFound <- err
				return
			}
			if !reflect.DeepEqual(output, []int64{42}) {
				errorsFound <- &Error{Stage: StageRun, Code: "TEST", Pos: Position{Line: 1, Column: 1}, Message: "wrong output"}
			}
		}()
	}
	group.Wait()
	close(errorsFound)
	for err := range errorsFound {
		t.Error(err)
	}
}
