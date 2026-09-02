package prefixforge

import (
	"fmt"
	"io"
)

func Run(code Bytecode, out io.Writer) (Value, error) {
	if err := verifyBytecode(code); err != nil {
		return Value{}, err
	}
	if out == nil {
		out = io.Discard
	}

	stack := make([]Value, 0, maxInt(1, code.MaxStack))
	ip := 0
	steps := 0
	pop := func(ins Instruction, want ValueType) (Value, error) {
		if len(stack) == 0 {
			return Value{}, stageError("vm", ins.At, "stack underflow at %s", ins.Op)
		}
		value := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if want != "" && value.Kind != want {
			return Value{}, stageError("vm", ins.At, "%s needs %s, got %s", ins.Op, want, value.Kind)
		}
		return value, nil
	}
	push := func(ins Instruction, value Value) error {
		if len(stack) >= MaxStackDepth {
			return stageError("vm", ins.At, "stack exceeds %d values", MaxStackDepth)
		}
		stack = append(stack, value)
		return nil
	}

	for {
		if steps >= MaxSteps {
			return Value{}, stageError("vm", code.Code[ip].At, "execution exceeds %d steps", MaxSteps)
		}
		steps++
		ins := code.Code[ip]
		switch ins.Op {
		case OpPushNumber:
			if err := push(ins, NumberValue(ins.Number)); err != nil {
				return Value{}, err
			}
			ip++
		case OpPushString:
			if err := push(ins, StringValue(ins.Text)); err != nil {
				return Value{}, err
			}
			ip++
		case OpPushBool:
			if err := push(ins, BoolValue(ins.Boolean)); err != nil {
				return Value{}, err
			}
			ip++
		case OpAdd, OpSub, OpMul, OpDiv:
			right, err := pop(ins, TypeNumber)
			if err != nil {
				return Value{}, err
			}
			left, err := pop(ins, TypeNumber)
			if err != nil {
				return Value{}, err
			}
			result, problem := checkedArithmetic(ins.Op, left.Number, right.Number)
			if problem != "" {
				return Value{}, stageError("vm", ins.At, "%s", problem)
			}
			if err := push(ins, NumberValue(result)); err != nil {
				return Value{}, err
			}
			ip++
		case OpLT:
			right, err := pop(ins, TypeNumber)
			if err != nil {
				return Value{}, err
			}
			left, err := pop(ins, TypeNumber)
			if err != nil {
				return Value{}, err
			}
			if err := push(ins, BoolValue(left.Number < right.Number)); err != nil {
				return Value{}, err
			}
			ip++
		case OpEQ:
			right, err := pop(ins, "")
			if err != nil {
				return Value{}, err
			}
			left, err := pop(ins, "")
			if err != nil {
				return Value{}, err
			}
			if left.Kind != right.Kind {
				return Value{}, stageError("vm", ins.At, "EQ operand types differ: %s and %s", left.Kind, right.Kind)
			}
			if err := push(ins, BoolValue(equalValues(left, right))); err != nil {
				return Value{}, err
			}
			ip++
		case OpNot:
			value, err := pop(ins, TypeBoolean)
			if err != nil {
				return Value{}, err
			}
			if err := push(ins, BoolValue(!value.Boolean)); err != nil {
				return Value{}, err
			}
			ip++
		case OpConcat:
			right, err := pop(ins, TypeString)
			if err != nil {
				return Value{}, err
			}
			left, err := pop(ins, TypeString)
			if err != nil {
				return Value{}, err
			}
			if err := push(ins, StringValue(left.Text+right.Text)); err != nil {
				return Value{}, err
			}
			ip++
		case OpJump:
			ip = ins.Target
		case OpJumpFalse, OpJumpTrue:
			condition, err := pop(ins, TypeBoolean)
			if err != nil {
				return Value{}, err
			}
			jump := (ins.Op == OpJumpFalse && !condition.Boolean) ||
				(ins.Op == OpJumpTrue && condition.Boolean)
			if jump {
				ip = ins.Target
			} else {
				ip++
			}
		case OpPrint:
			if len(stack) == 0 {
				return Value{}, stageError("vm", ins.At, "stack underflow at PRINT")
			}
			if _, err := fmt.Fprintln(out, stack[len(stack)-1].String()); err != nil {
				return Value{}, stageError("vm", ins.At, "write output: %v", err)
			}
			ip++
		case OpPop:
			if _, err := pop(ins, ""); err != nil {
				return Value{}, err
			}
			ip++
		case OpHalt:
			if len(stack) != 1 {
				return Value{}, stageError("vm", ins.At, "HALT requires exactly one value, got %d", len(stack))
			}
			return stack[0], nil
		default:
			return Value{}, stageError("vm", ins.At, "unknown opcode %q", ins.Op)
		}
	}
}

func equalValues(left, right Value) bool {
	switch left.Kind {
	case TypeNumber:
		return left.Number == right.Number
	case TypeString:
		return left.Text == right.Text
	case TypeBoolean:
		return left.Boolean == right.Boolean
	default:
		return false
	}
}

func maxInt(left, right int) int {
	if left > right {
		return left
	}
	return right
}
