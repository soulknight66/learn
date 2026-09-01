package pebble

func ValidateBytecode(code Bytecode) error {
	defaultPos := Position{Line: 1, Column: 1}
	if code.SlotCount < 0 {
		return languageError(StageValidate, CodeInvalidBytecode, firstInstructionPosition(code, defaultPos), "slot count is negative")
	}
	if len(code.Instructions) == 0 {
		return languageError(StageValidate, CodeInvalidBytecode, defaultPos, "instruction stream is empty")
	}

	initialized := make(map[int64]bool)
	depth := 0
	haltCount := 0
	for index, instruction := range code.Instructions {
		pos := instruction.Span.Start
		if !validSpan(instruction.Span) {
			return languageError(StageValidate, CodeInvalidBytecode, pos, "instruction span is invalid")
		}
		if instruction.Op != OpPush && instruction.Op != OpLoad && instruction.Op != OpStore && instruction.Operand != 0 {
			return languageError(StageValidate, CodeInvalidBytecode, pos, "opcode has an unexpected operand")
		}

		switch instruction.Op {
		case OpPush:
			depth++
		case OpLoad:
			if !validSlot(instruction.Operand, code.SlotCount) || !initialized[instruction.Operand] {
				return languageError(StageValidate, CodeInvalidBytecode, pos, "load uses an invalid or uninitialized slot")
			}
			depth++
		case OpStore:
			if !validSlot(instruction.Operand, code.SlotCount) || initialized[instruction.Operand] {
				return languageError(StageValidate, CodeInvalidBytecode, pos, "store uses an invalid or initialized slot")
			}
			if depth < 1 {
				return languageError(StageValidate, CodeInvalidBytecode, pos, "store would underflow the stack")
			}
			depth--
			initialized[instruction.Operand] = true
		case OpAdd, OpSub, OpMul, OpDiv:
			if depth < 2 {
				return languageError(StageValidate, CodeInvalidBytecode, pos, "arithmetic would underflow the stack")
			}
			depth--
		case OpPrint, OpPop:
			if depth < 1 {
				return languageError(StageValidate, CodeInvalidBytecode, pos, "instruction would underflow the stack")
			}
			depth--
		case OpHalt:
			haltCount++
			if index != len(code.Instructions)-1 || haltCount != 1 {
				return languageError(StageValidate, CodeInvalidBytecode, pos, "halt must occur exactly once at the end")
			}
			if depth != 0 {
				return languageError(StageValidate, CodeInvalidBytecode, pos, "stack must be empty at halt")
			}
		default:
			return languageError(StageValidate, CodeInvalidBytecode, pos, "unknown opcode")
		}
	}
	if haltCount != 1 {
		last := code.Instructions[len(code.Instructions)-1]
		return languageError(StageValidate, CodeInvalidBytecode, last.Span.Start, "instruction stream has no final halt")
	}
	return nil
}

func validSlot(operand int64, slotCount int) bool {
	return operand >= 0 && operand < int64(slotCount)
}

func firstInstructionPosition(code Bytecode, fallback Position) Position {
	if len(code.Instructions) > 0 && validPosition(code.Instructions[0].Span.Start) {
		return code.Instructions[0].Span.Start
	}
	return fallback
}
