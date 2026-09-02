package public_tests

import (
	"errors"
	"testing"

	pf "example.com/prefixforge"
)

func TestStage5DisassemblyIsStable(t *testing.T) {
	code := pf.Bytecode{Code: []pf.Instruction{
		{Op: pf.OpPushNumber, Number: 2},
		{Op: pf.OpJump, Target: 2},
		{Op: pf.OpHalt},
	}}
	want := "0000 PUSH_NUMBER    2\n0001 JUMP           0002\n0002 HALT          \n"
	if got := code.String(); got != want {
		t.Fatalf("disassembly:\n%q\nwant:\n%q", got, want)
	}
}

func TestStage5VMRejectsMalformedBytecode(t *testing.T) {
	cases := map[string]pf.Bytecode{
		"unknown opcode": {Code: []pf.Instruction{{Op: "NOPE"}}},
		"bad jump":       {Code: []pf.Instruction{{Op: pf.OpJump, Target: 99}}},
		"underflow":      {Code: []pf.Instruction{{Op: pf.OpAdd}, {Op: pf.OpHalt}}},
		"wrong operand": {Code: []pf.Instruction{
			{Op: pf.OpPushString, Text: "x"},
			{Op: pf.OpPushNumber, Number: 1},
			{Op: pf.OpAdd},
			{Op: pf.OpHalt},
		}},
	}
	for name, code := range cases {
		t.Run(name, func(t *testing.T) {
			_, err := pf.Run(code, nil)
			if err == nil {
				t.Fatal("malformed bytecode succeeded")
			}
			var stage *pf.StageError
			if !errors.As(err, &stage) || stage.Stage != "vm" {
				t.Fatalf("error = %T %v", err, err)
			}
		})
	}
}
