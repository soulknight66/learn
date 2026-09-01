package referencetests_test

import (
	"reflect"
	"testing"

	pebble "example.com/pebble-reference"
)

func FuzzExecuteNeverPanics(f *testing.F) {
	for _, seed := range []string{"", "(print 1)", "((", string([]byte{0xff, 0x00}), "# comment\n(+ 1 2)"} {
		f.Add(seed)
	}
	f.Fuzz(func(t *testing.T, source string) {
		_, _ = pebble.Execute(source)
	})
}

func FuzzValidateNeverPanicsOrMutates(f *testing.F) {
	f.Add([]byte{byte(pebble.OpHalt)})
	f.Add([]byte{byte(pebble.OpPush), byte(pebble.OpPop), byte(pebble.OpHalt)})
	f.Fuzz(func(t *testing.T, data []byte) {
		if len(data) > 128 {
			data = data[:128]
		}
		span := instructionSpan()
		instructions := make([]pebble.Instruction, len(data))
		for i, value := range data {
			instructions[i] = pebble.Instruction{Op: pebble.OpCode(value), Operand: int64(int8(value)), Span: span}
		}
		code := pebble.Bytecode{Instructions: instructions, SlotCount: len(data) % 4}
		before := pebble.Bytecode{Instructions: append([]pebble.Instruction(nil), instructions...), SlotCount: code.SlotCount}
		_ = pebble.ValidateBytecode(code)
		if !reflect.DeepEqual(code, before) {
			t.Fatal("ValidateBytecode mutated input")
		}
	})
}
