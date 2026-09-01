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
	// Opcode, operand, position, and slot-count inputs are independent. The
	// first two seeds are structurally valid, so validation reaches successful
	// halt and ordinary operational branches as well as rejection branches.
	f.Add([]byte{byte(pebble.OpHalt)}, []byte{0}, []byte{0, 0, 0, 1}, int64(0))
	f.Add(
		[]byte{byte(pebble.OpPush), byte(pebble.OpPop), byte(pebble.OpHalt)},
		[]byte{7, 0, 0},
		[]byte{0, 0, 0, 1, 1, 0, 0, 1, 2, 0, 0, 1},
		int64(0),
	)
	f.Add(
		[]byte{byte(pebble.OpPush), byte(pebble.OpStore), byte(pebble.OpHalt)},
		[]byte{1, 255, 0},
		[]byte{0, 0, 0, 1},
		int64(1),
	)
	f.Fuzz(func(t *testing.T, opcodes, operands, positions []byte, rawSlotCount int64) {
		count := len(opcodes)
		if len(operands) > count {
			count = len(operands)
		}
		if positionCount := (len(positions) + 3) / 4; positionCount > count {
			count = positionCount
		}
		if count > 128 {
			count = 128
		}
		instructions := make([]pebble.Instruction, count)
		for i := range instructions {
			opcode := byte(0)
			if i < len(opcodes) {
				opcode = opcodes[i]
			}
			operand := byte(0)
			if i < len(operands) {
				operand = operands[i]
			}
			instructions[i] = pebble.Instruction{
				Op:      pebble.OpCode(opcode),
				Operand: int64(int8(operand)),
				Span:    fuzzInstructionSpan(positions, i),
			}
		}
		code := pebble.Bytecode{Instructions: instructions, SlotCount: int(rawSlotCount % 8)}
		before := pebble.Bytecode{Instructions: append([]pebble.Instruction(nil), instructions...), SlotCount: code.SlotCount}
		_ = pebble.ValidateBytecode(code)
		if !reflect.DeepEqual(code, before) {
			t.Fatal("ValidateBytecode mutated input")
		}
	})
}

func fuzzInstructionSpan(data []byte, index int) pebble.Span {
	values := [4]byte{0, 0, 0, 1}
	for i := range values {
		position := index*len(values) + i
		if position < len(data) {
			values[i] = data[position]
		}
	}
	start := pebble.Position{
		Offset: int(values[0]),
		Line:   int(values[1]) + 1,
		Column: int(values[2]) + 1,
	}
	width := int(values[3])
	return pebble.Span{
		Start: start,
		End: pebble.Position{
			Offset: start.Offset + width,
			Line:   start.Line,
			Column: start.Column + width,
		},
	}
}
