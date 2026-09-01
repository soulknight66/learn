package publictests_test

import (
	"errors"
	"math"
	"reflect"
	"testing"

	pebble "example.com/pebble"
)

func requireLanguageError(t *testing.T, err error, stage pebble.Stage, code string, line, column int) *pebble.Error {
	t.Helper()
	if err == nil {
		t.Fatalf("error = nil, want %s/%s", stage, code)
	}
	var got *pebble.Error
	if !errors.As(err, &got) {
		t.Fatalf("error type = %T, want *pebble.Error", err)
	}
	if got.Stage != stage || got.Code != code || got.Pos.Line != line || got.Pos.Column != column {
		t.Fatalf("error = %#v, want %s/%s at %d:%d", got, stage, code, line, column)
	}
	return got
}

func TestScanKindsValuesAndBytePositions(t *testing.T) {
	tokens, err := pebble.Scan("# note\n(let x 12)")
	if err != nil {
		t.Fatal(err)
	}
	wantKinds := []pebble.TokenKind{
		pebble.TokenLParen, pebble.TokenLet, pebble.TokenIdentifier,
		pebble.TokenInteger, pebble.TokenRParen, pebble.TokenEOF,
	}
	if len(tokens) != len(wantKinds) {
		t.Fatalf("token count = %d, want %d: %#v", len(tokens), len(wantKinds), tokens)
	}
	for i, want := range wantKinds {
		if tokens[i].Kind != want {
			t.Errorf("token[%d].Kind = %v, want %v", i, tokens[i].Kind, want)
		}
	}
	if tokens[2].Lexeme != "x" || tokens[3].Integer != 12 {
		t.Fatalf("identifier/integer tokens = %#v / %#v", tokens[2], tokens[3])
	}
	if got := tokens[0].Span.Start; got != (pebble.Position{Offset: 7, Line: 2, Column: 1}) {
		t.Errorf("left parenthesis start = %#v", got)
	}
	if got := tokens[3].Span; got.Start.Offset != 14 || got.End.Offset != 16 || got.Start.Column != 8 || got.End.Column != 10 {
		t.Errorf("integer span = %#v", got)
	}
	if got := tokens[5].Span; got.Start.Offset != 17 || got.End.Offset != 17 || got.Start.Column != 11 {
		t.Errorf("EOF span = %#v", got)
	}
}

func TestScanRejectsBadByteAndLargeInteger(t *testing.T) {
	_, err := pebble.Scan("(print 1)\n@")
	requireLanguageError(t, err, pebble.StageScan, pebble.CodeInvalidChar, 2, 1)

	_, err = pebble.Scan("9223372036854775808")
	requireLanguageError(t, err, pebble.StageScan, pebble.CodeIntegerRange, 1, 1)

	_, err = pebble.Scan(string([]byte{0xff}))
	requireLanguageError(t, err, pebble.StageScan, pebble.CodeInvalidChar, 1, 1)
}

func TestParseBuildsNestedBinaryTree(t *testing.T) {
	tokens, err := pebble.Scan("(print (+ 2 (* 3 4)))")
	if err != nil {
		t.Fatal(err)
	}
	program, err := pebble.Parse(tokens)
	if err != nil {
		t.Fatal(err)
	}
	if len(program.Statements) != 1 || program.Statements[0].Kind != pebble.StmtPrint {
		t.Fatalf("statements = %#v", program.Statements)
	}
	expr := program.Statements[0].Expr
	if expr == nil || expr.Kind != pebble.ExprBinary || expr.Op != pebble.TokenPlus || expr.Left.Integer != 2 {
		t.Fatalf("outer expression = %#v", expr)
	}
	if expr.Right == nil || expr.Right.Kind != pebble.ExprBinary || expr.Right.Op != pebble.TokenStar || expr.Right.Right.Integer != 4 {
		t.Fatalf("right expression = %#v", expr.Right)
	}
	if program.Statements[0].Span.Start.Offset != 0 || program.Statements[0].Span.End.Offset != 21 {
		t.Errorf("statement span = %#v", program.Statements[0].Span)
	}
}

func TestParseRejectsTruncationAndForgedStreams(t *testing.T) {
	tokens, err := pebble.Scan("(print (+ 1 2)")
	if err != nil {
		t.Fatal(err)
	}
	_, err = pebble.Parse(tokens)
	requireLanguageError(t, err, pebble.StageParse, pebble.CodeExpectedToken, 1, 15)

	_, err = pebble.Parse(nil)
	requireLanguageError(t, err, pebble.StageParse, pebble.CodeInvalidTokenStream, 1, 1)
}

func TestAnalyzeSlotsAndVisibility(t *testing.T) {
	tokens, _ := pebble.Scan("(let z 1) (let a (+ z 2)) (print a)")
	program, err := pebble.Parse(tokens)
	if err != nil {
		t.Fatal(err)
	}
	analysis, err := pebble.Analyze(program)
	if err != nil {
		t.Fatal(err)
	}
	if analysis.SlotCount != 2 || analysis.Slots["z"] != 0 || analysis.Slots["a"] != 1 {
		t.Fatalf("analysis = %#v", analysis)
	}

	tokens, _ = pebble.Scan("(let x x)")
	program, _ = pebble.Parse(tokens)
	_, err = pebble.Analyze(program)
	requireLanguageError(t, err, pebble.StageAnalyze, pebble.CodeUndefinedName, 1, 8)
}

func TestCompileUsesSpecifiedInstructionOrder(t *testing.T) {
	tokens, _ := pebble.Scan("(let x 2) (print (+ x 3))")
	program, _ := pebble.Parse(tokens)
	analysis, _ := pebble.Analyze(program)
	code, err := pebble.Compile(program, analysis)
	if err != nil {
		t.Fatal(err)
	}
	wantOps := []pebble.OpCode{
		pebble.OpPush, pebble.OpStore, pebble.OpLoad, pebble.OpPush,
		pebble.OpAdd, pebble.OpPrint, pebble.OpHalt,
	}
	gotOps := make([]pebble.OpCode, len(code.Instructions))
	for i, instruction := range code.Instructions {
		gotOps[i] = instruction.Op
	}
	if !reflect.DeepEqual(gotOps, wantOps) {
		t.Fatalf("opcodes = %v, want %v", gotOps, wantOps)
	}
	if code.SlotCount != 1 || code.Instructions[1].Operand != 0 || code.Instructions[2].Operand != 0 {
		t.Fatalf("bytecode slots = %#v", code)
	}
}

func TestExecuteEndToEnd(t *testing.T) {
	source := "(let width 6)\n(let height (+ width 4))\n(print (* width height))"
	got, err := pebble.Execute(source)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(got, []int64{60}) {
		t.Fatalf("output = %v, want [60]", got)
	}

	got, err = pebble.Execute("(+ 1 2)")
	if err != nil || got == nil || len(got) != 0 {
		t.Fatalf("expression-only output/error = %#v / %v", got, err)
	}
}

func TestRuntimeErrorsAreCheckedAndTransactional(t *testing.T) {
	output, err := pebble.Execute("(print 1)\n(print (/ 9 0))")
	if output != nil {
		t.Fatalf("failure output = %v, want nil", output)
	}
	requireLanguageError(t, err, pebble.StageRun, pebble.CodeDivisionByZero, 2, 8)

	output, err = pebble.Execute("(print (+ 9223372036854775807 1))")
	if output != nil {
		t.Fatalf("overflow output = %v, want nil", output)
	}
	requireLanguageError(t, err, pebble.StageRun, pebble.CodeIntegerOverflow, 1, 8)
}

func TestValidateRejectsUnsafeBytecode(t *testing.T) {
	span := pebble.Span{
		Start: pebble.Position{Offset: 0, Line: 1, Column: 1},
		End:   pebble.Position{Offset: 1, Line: 1, Column: 2},
	}
	bad := pebble.Bytecode{Instructions: []pebble.Instruction{
		{Op: pebble.OpLoad, Operand: 0, Span: span},
		{Op: pebble.OpPop, Span: span},
		{Op: pebble.OpHalt, Span: span},
	}, SlotCount: 1}
	err := pebble.ValidateBytecode(bad)
	requireLanguageError(t, err, pebble.StageValidate, pebble.CodeInvalidBytecode, 1, 1)

	bad = pebble.Bytecode{Instructions: []pebble.Instruction{
		{Op: pebble.OpPush, Operand: math.MaxInt64, Span: span},
		{Op: pebble.OpHalt, Span: span},
	}}
	err = pebble.ValidateBytecode(bad)
	requireLanguageError(t, err, pebble.StageValidate, pebble.CodeInvalidBytecode, 1, 1)
}
