package learnervalidation_test

import (
	"errors"
	"math"
	"reflect"
	"sync"
	"testing"

	pebble "example.com/pebble"
)

func requireLanguageError(t *testing.T, err error, stage pebble.Stage, code string) *pebble.Error {
	t.Helper()
	if err == nil {
		t.Fatalf("error = nil, want %s/%s", stage, code)
	}
	var got *pebble.Error
	if !errors.As(err, &got) {
		t.Fatalf("error type = %T, want *pebble.Error", err)
	}
	if got.Stage != stage || got.Code != code {
		t.Fatalf("error = %#v, want %s/%s", got, stage, code)
	}
	return got
}

func validSpan() pebble.Span {
	return pebble.Span{
		Start: pebble.Position{Offset: 0, Line: 1, Column: 1},
		End:   pebble.Position{Offset: 1, Line: 1, Column: 2},
	}
}

func TestEmptyProgramScannerAndPipeline(t *testing.T) {
	tokens, err := pebble.Scan("")
	if err != nil {
		t.Fatal(err)
	}
	position := pebble.Position{Offset: 0, Line: 1, Column: 1}
	if len(tokens) != 1 || tokens[0].Kind != pebble.TokenEOF ||
		tokens[0].Span != (pebble.Span{Start: position, End: position}) {
		t.Fatalf("tokens = %#v", tokens)
	}
	code, err := pebble.Build("")
	if err != nil {
		t.Fatal(err)
	}
	if len(code.Instructions) != 1 || code.Instructions[0].Op != pebble.OpHalt {
		t.Fatalf("bytecode = %#v", code)
	}
	output, err := pebble.Execute("")
	if err != nil || output == nil || len(output) != 0 {
		t.Fatalf("Execute = %#v, %v", output, err)
	}
}

func TestImpossibleLineChangingTokenGapIsRejected(t *testing.T) {
	tokens := []pebble.Token{
		{
			Kind: pebble.TokenInteger, Lexeme: "1", Integer: 1,
			Span: pebble.Span{
				Start: pebble.Position{Offset: 1, Line: 2, Column: 99},
				End:   pebble.Position{Offset: 2, Line: 2, Column: 100},
			},
		},
		{Kind: pebble.TokenEOF, Span: pebble.Span{
			Start: pebble.Position{Offset: 2, Line: 2, Column: 100},
			End:   pebble.Position{Offset: 2, Line: 2, Column: 100},
		}},
	}
	_, err := pebble.Parse(tokens)
	got := requireLanguageError(t, err, pebble.StageParse, pebble.CodeInvalidTokenStream)
	if got.Pos.Line != 2 || got.Pos.Column != 99 {
		t.Fatalf("position = %#v", got.Pos)
	}
}

func TestAnalysisErrorPrecedenceAndCompileDeterminism(t *testing.T) {
	tokens, err := pebble.Scan("(let x 1) (let x missing)")
	if err != nil {
		t.Fatal(err)
	}
	program, err := pebble.Parse(tokens)
	if err != nil {
		t.Fatal(err)
	}
	_, err = pebble.Analyze(program)
	got := requireLanguageError(t, err, pebble.StageAnalyze, pebble.CodeRedeclaredName)
	if got.Pos.Line != 1 || got.Pos.Column != 16 {
		t.Fatalf("position = %#v", got.Pos)
	}

	source := "(let a 2) (let b (+ a 3)) (print (* a b))"
	first, err := pebble.Build(source)
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 20; i++ {
		next, err := pebble.Build(source)
		if err != nil {
			t.Fatal(err)
		}
		if !reflect.DeepEqual(first, next) {
			t.Fatalf("build %d differs", i)
		}
	}
}

func TestNegativeAndOutOfRangeSlotsAreRejected(t *testing.T) {
	span := validSpan()
	for _, operand := range []int64{-1, 1, math.MaxInt64} {
		code := pebble.Bytecode{
			Instructions: []pebble.Instruction{
				{Op: pebble.OpPush, Operand: 7, Span: span},
				{Op: pebble.OpStore, Operand: operand, Span: span},
				{Op: pebble.OpHalt, Span: span},
			},
			SlotCount: 1,
		}
		before := pebble.Bytecode{Instructions: append([]pebble.Instruction(nil), code.Instructions...), SlotCount: code.SlotCount}
		err := pebble.ValidateBytecode(code)
		requireLanguageError(t, err, pebble.StageValidate, pebble.CodeInvalidBytecode)
		if !reflect.DeepEqual(code, before) {
			t.Fatalf("operand %d: validator mutated input", operand)
		}
	}
}

func TestArithmeticBoundariesAndTransactionalOutput(t *testing.T) {
	span := validSpan()
	tests := []struct {
		name       string
		left       int64
		right      int64
		op         pebble.OpCode
		code       string
		withPrefix bool
	}{
		{"add overflow", math.MaxInt64, 1, pebble.OpAdd, pebble.CodeIntegerOverflow, false},
		{"subtract overflow", math.MinInt64, 1, pebble.OpSub, pebble.CodeIntegerOverflow, false},
		{"multiply overflow", math.MaxInt64, 2, pebble.OpMul, pebble.CodeIntegerOverflow, false},
		{"division overflow", math.MinInt64, -1, pebble.OpDiv, pebble.CodeIntegerOverflow, false},
		{"division by zero after print", 8, 0, pebble.OpDiv, pebble.CodeDivisionByZero, true},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			instructions := make([]pebble.Instruction, 0, 7)
			if test.withPrefix {
				instructions = append(instructions,
					pebble.Instruction{Op: pebble.OpPush, Operand: 7, Span: span},
					pebble.Instruction{Op: pebble.OpPrint, Span: span},
				)
			}
			instructions = append(instructions,
				pebble.Instruction{Op: pebble.OpPush, Operand: test.left, Span: span},
				pebble.Instruction{Op: pebble.OpPush, Operand: test.right, Span: span},
				pebble.Instruction{Op: test.op, Span: span},
				pebble.Instruction{Op: pebble.OpPrint, Span: span},
				pebble.Instruction{Op: pebble.OpHalt, Span: span},
			)
			output, err := pebble.Run(pebble.Bytecode{Instructions: instructions})
			if output != nil {
				t.Fatalf("output = %#v, want nil", output)
			}
			requireLanguageError(t, err, pebble.StageRun, test.code)
		})
	}
}

func TestConcurrentRunUsesFreshStateAndPreservesInput(t *testing.T) {
	code, err := pebble.Build("(let x 21) (print (* x 2))")
	if err != nil {
		t.Fatal(err)
	}
	before := pebble.Bytecode{Instructions: append([]pebble.Instruction(nil), code.Instructions...), SlotCount: code.SlotCount}
	const workers = 16
	errCh := make(chan error, workers)
	var group sync.WaitGroup
	for i := 0; i < workers; i++ {
		group.Add(1)
		go func() {
			defer group.Done()
			output, err := pebble.Run(code)
			if err != nil {
				errCh <- err
				return
			}
			if !reflect.DeepEqual(output, []int64{42}) {
				errCh <- errors.New("wrong output")
			}
		}()
	}
	group.Wait()
	close(errCh)
	for err := range errCh {
		t.Error(err)
	}
	if !reflect.DeepEqual(code, before) {
		t.Fatal("Run mutated bytecode")
	}
}
