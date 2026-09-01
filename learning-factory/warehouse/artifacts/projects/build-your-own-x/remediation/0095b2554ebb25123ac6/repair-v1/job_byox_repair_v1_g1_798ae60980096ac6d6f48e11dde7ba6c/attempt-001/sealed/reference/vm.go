package pebble

import "math"

func Run(code Bytecode) ([]int64, error) {
	if err := ValidateBytecode(code); err != nil {
		return nil, err
	}
	stack := make([]int64, 0)
	locals := make(map[int64]int64)
	output := make([]int64, 0)
	for _, instruction := range code.Instructions {
		switch instruction.Op {
		case OpPush:
			stack = append(stack, instruction.Operand)
		case OpLoad:
			stack = append(stack, locals[instruction.Operand])
		case OpStore:
			value := stack[len(stack)-1]
			stack = stack[:len(stack)-1]
			locals[instruction.Operand] = value
		case OpAdd, OpSub, OpMul, OpDiv:
			right := stack[len(stack)-1]
			left := stack[len(stack)-2]
			stack = stack[:len(stack)-2]
			value, code := calculate(instruction.Op, left, right)
			if code != "" {
				message := "integer arithmetic overflow"
				if code == CodeDivisionByZero {
					message = "division by zero"
				}
				return nil, languageError(StageRun, code, instruction.Span.Start, message)
			}
			stack = append(stack, value)
		case OpPrint:
			value := stack[len(stack)-1]
			stack = stack[:len(stack)-1]
			output = append(output, value)
		case OpPop:
			stack = stack[:len(stack)-1]
		case OpHalt:
			return output, nil
		}
	}
	return nil, languageError(StageValidate, CodeInvalidBytecode, Position{Line: 1, Column: 1}, "validated stream did not halt")
}

func calculate(op OpCode, left, right int64) (int64, string) {
	switch op {
	case OpAdd:
		if right > 0 && left > math.MaxInt64-right || right < 0 && left < math.MinInt64-right {
			return 0, CodeIntegerOverflow
		}
		return left + right, ""
	case OpSub:
		if right > 0 && left < math.MinInt64+right || right < 0 && left > math.MaxInt64+right {
			return 0, CodeIntegerOverflow
		}
		return left - right, ""
	case OpMul:
		if left == 0 || right == 0 {
			return 0, ""
		}
		if left == -1 && right == math.MinInt64 || right == -1 && left == math.MinInt64 {
			return 0, CodeIntegerOverflow
		}
		value := left * right
		if value/right != left {
			return 0, CodeIntegerOverflow
		}
		return value, ""
	case OpDiv:
		if right == 0 {
			return 0, CodeDivisionByZero
		}
		if left == math.MinInt64 && right == -1 {
			return 0, CodeIntegerOverflow
		}
		return left / right, ""
	default:
		return 0, CodeIntegerOverflow
	}
}
