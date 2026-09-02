package prefixforge

type abstractStack struct {
	parent *abstractStack
	kind   ValueType
	depth  int
}

type abstractStackKey struct {
	parent *abstractStack
	kind   ValueType
}

func verifyBytecode(code Bytecode) error {
	if len(code.Code) == 0 {
		return stageError("vm", initialSpan(), "bytecode is empty")
	}
	if len(code.Code) > MaxInstructions {
		return stageError("vm", initialSpan(), "instruction count exceeds %d", MaxInstructions)
	}
	if code.MaxStack < 0 || code.MaxStack > MaxStackDepth {
		return stageError("vm", initialSpan(), "invalid declared maximum stack %d", code.MaxStack)
	}
	for _, ins := range code.Code {
		if !knownOpcode(ins.Op) {
			return stageError("vm", ins.At, "unknown opcode %q", ins.Op)
		}
		if ins.Op == OpJump || ins.Op == OpJumpFalse || ins.Op == OpJumpTrue {
			if ins.Target < 0 || ins.Target >= len(code.Code) {
				return stageError("vm", ins.At, "invalid jump target %d", ins.Target)
			}
		}
	}

	states := make([]*abstractStack, len(code.Code))
	seen := make([]bool, len(code.Code))
	queue := []int{0}
	seen[0] = true
	interned := make(map[abstractStackKey]*abstractStack)

	propagate := func(from, target int, stack *abstractStack) error {
		if target < 0 || target >= len(code.Code) {
			return stageError("vm", code.Code[from].At, "control flow leaves bytecode")
		}
		if !seen[target] {
			seen[target] = true
			states[target] = stack
			queue = append(queue, target)
			return nil
		}
		if states[target] != stack {
			return stageError("vm", code.Code[target].At, "inconsistent stack types at control-flow join")
		}
		return nil
	}

	for len(queue) > 0 {
		ip := queue[0]
		queue = queue[1:]
		ins := code.Code[ip]
		stack := states[ip]
		pop := func(want ValueType) error {
			if stack == nil {
				return stageError("vm", ins.At, "stack underflow at %s", ins.Op)
			}
			got := stack.kind
			stack = stack.parent
			if want != "" && got != want {
				return stageError("vm", ins.At, "%s needs %s, got %s", ins.Op, want, got)
			}
			return nil
		}
		push := func(typ ValueType) error {
			depth := 1
			if stack != nil {
				depth = stack.depth + 1
			}
			if depth > MaxStackDepth {
				return stageError("vm", ins.At, "stack exceeds %d values", MaxStackDepth)
			}
			key := abstractStackKey{parent: stack, kind: typ}
			node := interned[key]
			if node == nil {
				node = &abstractStack{parent: stack, kind: typ, depth: depth}
				interned[key] = node
			}
			stack = node
			return nil
		}
		fallsThrough := true
		switch ins.Op {
		case OpPushNumber:
			if err := push(TypeNumber); err != nil {
				return err
			}
		case OpPushString:
			if err := push(TypeString); err != nil {
				return err
			}
		case OpPushBool:
			if err := push(TypeBoolean); err != nil {
				return err
			}
		case OpAdd, OpSub, OpMul, OpDiv, OpLT:
			if err := pop(TypeNumber); err != nil {
				return err
			}
			if err := pop(TypeNumber); err != nil {
				return err
			}
			result := TypeNumber
			if ins.Op == OpLT {
				result = TypeBoolean
			}
			if err := push(result); err != nil {
				return err
			}
		case OpConcat:
			if err := pop(TypeString); err != nil {
				return err
			}
			if err := pop(TypeString); err != nil {
				return err
			}
			if err := push(TypeString); err != nil {
				return err
			}
		case OpEQ:
			if stack == nil || stack.parent == nil {
				return stageError("vm", ins.At, "stack underflow at %s", ins.Op)
			}
			right := stack.kind
			left := stack.parent.kind
			if left != right {
				return stageError("vm", ins.At, "EQ operand types differ: %s and %s", left, right)
			}
			stack = stack.parent.parent
			if err := push(TypeBoolean); err != nil {
				return err
			}
		case OpNot:
			if err := pop(TypeBoolean); err != nil {
				return err
			}
			if err := push(TypeBoolean); err != nil {
				return err
			}
		case OpPrint:
			if stack == nil {
				return stageError("vm", ins.At, "stack underflow at PRINT")
			}
		case OpPop:
			if err := pop(""); err != nil {
				return err
			}
		case OpJump:
			fallsThrough = false
			if err := propagate(ip, ins.Target, stack); err != nil {
				return err
			}
		case OpJumpFalse, OpJumpTrue:
			if err := pop(TypeBoolean); err != nil {
				return err
			}
			if err := propagate(ip, ins.Target, stack); err != nil {
				return err
			}
		case OpHalt:
			fallsThrough = false
			depth := 0
			if stack != nil {
				depth = stack.depth
			}
			if depth != 1 {
				return stageError("vm", ins.At, "HALT requires exactly one value, got %d", depth)
			}
		}
		if fallsThrough {
			if err := propagate(ip, ip+1, stack); err != nil {
				return err
			}
		}
	}
	return nil
}

func knownOpcode(op OpCode) bool {
	switch op {
	case OpPushNumber, OpPushString, OpPushBool,
		OpAdd, OpSub, OpMul, OpDiv, OpLT, OpEQ, OpNot, OpConcat,
		OpJump, OpJumpFalse, OpJumpTrue, OpPrint, OpPop, OpHalt:
		return true
	default:
		return false
	}
}
