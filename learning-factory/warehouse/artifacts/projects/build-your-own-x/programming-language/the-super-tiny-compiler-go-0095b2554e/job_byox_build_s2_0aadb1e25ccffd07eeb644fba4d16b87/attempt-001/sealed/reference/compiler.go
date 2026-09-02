package prefixforge

type compiler struct {
	code     []Instruction
	depth    int
	maxDepth int
}

func Compile(program Program) (Bytecode, error) {
	if _, err := Check(program); err != nil {
		return Bytecode{}, err
	}
	c := &compiler{}
	for i, expr := range program.Exprs {
		if err := c.compileExpr(expr, 0); err != nil {
			return Bytecode{}, err
		}
		if i < len(program.Exprs)-1 {
			if _, err := c.emit(Instruction{Op: OpPop, At: spanOf(expr)}); err != nil {
				return Bytecode{}, err
			}
			if err := c.drop(1, spanOf(expr)); err != nil {
				return Bytecode{}, err
			}
		}
	}
	if c.depth != 1 {
		return Bytecode{}, stageError("compile", program.At, "internal stack depth is %d at halt", c.depth)
	}
	if _, err := c.emit(Instruction{Op: OpHalt, At: program.At}); err != nil {
		return Bytecode{}, err
	}
	return Bytecode{Code: c.code, MaxStack: c.maxDepth}, nil
}

func (c *compiler) compileExpr(expr Expr, depth int) error {
	switch n := expr.(type) {
	case NumberExpr:
		return c.emitNumber(n)
	case *NumberExpr:
		if n == nil {
			return stageError("compile", initialSpan(), "nil number expression")
		}
		return c.emitNumber(*n)
	case StringExpr:
		return c.emitString(n)
	case *StringExpr:
		if n == nil {
			return stageError("compile", initialSpan(), "nil string expression")
		}
		return c.emitString(*n)
	case BoolExpr:
		return c.emitBool(n)
	case *BoolExpr:
		if n == nil {
			return stageError("compile", initialSpan(), "nil boolean expression")
		}
		return c.emitBool(*n)
	case CallExpr:
		return c.compileCall(n, depth)
	case *CallExpr:
		if n == nil {
			return stageError("compile", initialSpan(), "nil call expression")
		}
		return c.compileCall(*n, depth)
	default:
		return stageError("compile", spanOf(expr), "unsupported expression node")
	}
}

func (c *compiler) emitNumber(n NumberExpr) error {
	if _, err := c.emit(Instruction{Op: OpPushNumber, Number: n.Value, At: n.At}); err != nil {
		return err
	}
	return c.grow(n.At)
}

func (c *compiler) emitString(n StringExpr) error {
	if _, err := c.emit(Instruction{Op: OpPushString, Text: n.Value, At: n.At}); err != nil {
		return err
	}
	return c.grow(n.At)
}

func (c *compiler) emitBool(n BoolExpr) error {
	if _, err := c.emit(Instruction{Op: OpPushBool, Boolean: n.Value, At: n.At}); err != nil {
		return err
	}
	return c.grow(n.At)
}

func (c *compiler) compileCall(call CallExpr, depth int) error {
	if depth >= MaxNesting {
		return stageError("compile", call.At, "call nesting exceeds %d", MaxNesting)
	}
	switch call.Name {
	case "if":
		return c.compileIf(call, depth)
	case "and":
		return c.compileShortCircuit(call, depth, false)
	case "or":
		return c.compileShortCircuit(call, depth, true)
	}

	for _, arg := range call.Args {
		if err := c.compileExpr(arg, depth+1); err != nil {
			return err
		}
	}
	op, ok := eagerOpcode(call.Name)
	if !ok {
		return stageError("compile", call.NameSpan, "cannot emit unknown built-in %q", call.Name)
	}
	if _, err := c.emit(Instruction{Op: op, At: call.At}); err != nil {
		return err
	}
	switch call.Name {
	case "add", "sub", "mul", "div", "lt", "eq", "concat":
		return c.drop(1, call.At) // two operands become one value
	case "not", "print":
		return nil // one operand remains one value
	default:
		return stageError("compile", call.At, "unsupported stack effect for %q", call.Name)
	}
}

func (c *compiler) compileIf(call CallExpr, depth int) error {
	base := c.depth
	if err := c.compileExpr(call.Args[0], depth+1); err != nil {
		return err
	}
	jumpFalse, err := c.emit(Instruction{Op: OpJumpFalse, Target: -1, At: call.At})
	if err != nil {
		return err
	}
	if err := c.drop(1, call.At); err != nil {
		return err
	}
	if err := c.compileExpr(call.Args[1], depth+1); err != nil {
		return err
	}
	jumpEnd, err := c.emit(Instruction{Op: OpJump, Target: -1, At: call.At})
	if err != nil {
		return err
	}
	if c.depth != base+1 {
		return stageError("compile", call.At, "then branch has invalid stack effect")
	}
	c.code[jumpFalse].Target = len(c.code)
	c.depth = base
	if err := c.compileExpr(call.Args[2], depth+1); err != nil {
		return err
	}
	if c.depth != base+1 {
		return stageError("compile", call.At, "else branch has invalid stack effect")
	}
	c.code[jumpEnd].Target = len(c.code)
	return nil
}

func (c *compiler) compileShortCircuit(call CallExpr, depth int, jumpOnTrue bool) error {
	base := c.depth
	if err := c.compileExpr(call.Args[0], depth+1); err != nil {
		return err
	}
	conditional := OpJumpFalse
	constant := false
	if jumpOnTrue {
		conditional = OpJumpTrue
		constant = true
	}
	jumpConstant, err := c.emit(Instruction{Op: conditional, Target: -1, At: call.At})
	if err != nil {
		return err
	}
	if err := c.drop(1, call.At); err != nil {
		return err
	}
	if err := c.compileExpr(call.Args[1], depth+1); err != nil {
		return err
	}
	jumpEnd, err := c.emit(Instruction{Op: OpJump, Target: -1, At: call.At})
	if err != nil {
		return err
	}
	if c.depth != base+1 {
		return stageError("compile", call.At, "short-circuit value has invalid stack effect")
	}
	c.code[jumpConstant].Target = len(c.code)
	c.depth = base
	if _, err := c.emit(Instruction{Op: OpPushBool, Boolean: constant, At: call.At}); err != nil {
		return err
	}
	if err := c.grow(call.At); err != nil {
		return err
	}
	c.code[jumpEnd].Target = len(c.code)
	return nil
}

func eagerOpcode(name string) (OpCode, bool) {
	switch name {
	case "add":
		return OpAdd, true
	case "sub":
		return OpSub, true
	case "mul":
		return OpMul, true
	case "div":
		return OpDiv, true
	case "lt":
		return OpLT, true
	case "eq":
		return OpEQ, true
	case "not":
		return OpNot, true
	case "concat":
		return OpConcat, true
	case "print":
		return OpPrint, true
	default:
		return "", false
	}
}

func (c *compiler) emit(ins Instruction) (int, error) {
	if len(c.code) >= MaxInstructions {
		return 0, stageError("compile", ins.At, "instruction limit %d exceeded", MaxInstructions)
	}
	index := len(c.code)
	c.code = append(c.code, ins)
	return index, nil
}

func (c *compiler) grow(at Span) error {
	c.depth++
	if c.depth > MaxStackDepth {
		return stageError("compile", at, "stack depth exceeds %d", MaxStackDepth)
	}
	if c.depth > c.maxDepth {
		c.maxDepth = c.depth
	}
	return nil
}

func (c *compiler) drop(count int, at Span) error {
	if count < 0 || c.depth < count {
		return stageError("compile", at, "internal stack underflow")
	}
	c.depth -= count
	return nil
}
