package referencetests_test

import (
	"reflect"
	"testing"

	pebble "example.com/pebble-reference"
)

func instructionSpan() pebble.Span {
	return pebble.Span{
		Start: pebble.Position{Offset: 0, Line: 1, Column: 1},
		End:   pebble.Position{Offset: 1, Line: 1, Column: 2},
	}
}

func TestAdversarialBytecodeTable(t *testing.T) {
	span := instructionSpan()
	tests := []struct {
		name string
		code pebble.Bytecode
	}{
		{"empty", pebble.Bytecode{}},
		{"negative slots", pebble.Bytecode{Instructions: []pebble.Instruction{{Op: pebble.OpHalt, Span: span}}, SlotCount: -1}},
		{"unknown opcode", pebble.Bytecode{Instructions: []pebble.Instruction{{Op: pebble.OpCode(200), Span: span}, {Op: pebble.OpHalt, Span: span}}}},
		{"early halt", pebble.Bytecode{Instructions: []pebble.Instruction{{Op: pebble.OpHalt, Span: span}, {Op: pebble.OpHalt, Span: span}}}},
		{"no halt", pebble.Bytecode{Instructions: []pebble.Instruction{{Op: pebble.OpPush, Operand: 1, Span: span}, {Op: pebble.OpPop, Span: span}}}},
		{"stack residue", pebble.Bytecode{Instructions: []pebble.Instruction{{Op: pebble.OpPush, Operand: 1, Span: span}, {Op: pebble.OpHalt, Span: span}}}},
		{"pop underflow", pebble.Bytecode{Instructions: []pebble.Instruction{{Op: pebble.OpPop, Span: span}, {Op: pebble.OpHalt, Span: span}}}},
		{"bad local", pebble.Bytecode{Instructions: []pebble.Instruction{{Op: pebble.OpLoad, Operand: 0, Span: span}, {Op: pebble.OpPop, Span: span}, {Op: pebble.OpHalt, Span: span}}, SlotCount: 1}},
		{"duplicate store", pebble.Bytecode{Instructions: []pebble.Instruction{{Op: pebble.OpPush, Operand: 1, Span: span}, {Op: pebble.OpStore, Span: span}, {Op: pebble.OpPush, Operand: 2, Span: span}, {Op: pebble.OpStore, Span: span}, {Op: pebble.OpHalt, Span: span}}, SlotCount: 1}},
		{"stray operand", pebble.Bytecode{Instructions: []pebble.Instruction{{Op: pebble.OpHalt, Operand: 1, Span: span}}}},
		{"zero position", pebble.Bytecode{Instructions: []pebble.Instruction{{Op: pebble.OpHalt}}}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			before := pebble.Bytecode{Instructions: append([]pebble.Instruction(nil), test.code.Instructions...), SlotCount: test.code.SlotCount}
			err := pebble.ValidateBytecode(test.code)
			assertError(t, err, pebble.StageValidate, pebble.CodeInvalidBytecode)
			if !reflect.DeepEqual(test.code, before) {
				t.Fatalf("validator mutated input")
			}
			if output, err := pebble.Run(test.code); output != nil || err == nil {
				t.Fatalf("Run = %#v, %v", output, err)
			}
		})
	}
}

func TestHugeUnusedSlotCountDoesNotDriveAllocation(t *testing.T) {
	span := instructionSpan()
	maxInt := int(^uint(0) >> 1)
	code := pebble.Bytecode{
		Instructions: []pebble.Instruction{{Op: pebble.OpHalt, Span: span}},
		SlotCount:    maxInt,
	}
	if err := pebble.ValidateBytecode(code); err != nil {
		t.Fatal(err)
	}
	output, err := pebble.Run(code)
	if err != nil || output == nil || len(output) != 0 {
		t.Fatalf("Run = %#v, %v", output, err)
	}
}
