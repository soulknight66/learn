package reference_tests

import (
	"errors"
	"testing"

	pf "example.com/prefixforge"
)

func TestVMRejectsAdversarialBytecode(t *testing.T) {
	tooDeep := make([]pf.Instruction, pf.MaxStackDepth+2)
	for i := 0; i <= pf.MaxStackDepth; i++ {
		tooDeep[i] = pf.Instruction{Op: pf.OpPushNumber}
	}
	tooDeep[len(tooDeep)-1] = pf.Instruction{Op: pf.OpHalt}
	cases := map[string]pf.Bytecode{
		"empty": {},
		"unknown": {Code: []pf.Instruction{
			{Op: pf.OpPushNumber}, {Op: "CORRUPT"},
		}},
		"jump target": {Code: []pf.Instruction{
			{Op: pf.OpJump, Target: -1},
		}},
		"underflow": {Code: []pf.Instruction{
			{Op: pf.OpPop}, {Op: pf.OpHalt},
		}},
		"kind": {Code: []pf.Instruction{
			{Op: pf.OpPushString}, {Op: pf.OpNot}, {Op: pf.OpHalt},
		}},
		"halt shape": {Code: []pf.Instruction{
			{Op: pf.OpPushNumber}, {Op: pf.OpPushNumber}, {Op: pf.OpHalt},
		}},
		"fall off end": {Code: []pf.Instruction{
			{Op: pf.OpPushNumber},
		}},
		"stack depth": {Code: tooDeep},
		"join mismatch": {Code: []pf.Instruction{
			{Op: pf.OpPushBool, Boolean: true},
			{Op: pf.OpJumpFalse, Target: 4},
			{Op: pf.OpPushNumber},
			{Op: pf.OpJump, Target: 5},
			{Op: pf.OpPushString},
			{Op: pf.OpHalt},
		}},
	}
	for name, code := range cases {
		t.Run(name, func(t *testing.T) {
			_, err := pf.Run(code, nil)
			if err == nil {
				t.Fatal("Run succeeded")
			}
			var stage *pf.StageError
			if !errors.As(err, &stage) || stage.Stage != "vm" {
				t.Fatalf("error = %T %v", err, err)
			}
		})
	}
}

func TestVMLoopHitsStepLimit(t *testing.T) {
	code := pf.Bytecode{Code: []pf.Instruction{{Op: pf.OpJump, Target: 0}}}
	if _, err := pf.Run(code, nil); err == nil {
		t.Fatal("infinite loop succeeded")
	}
}
