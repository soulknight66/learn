package pebble

func Compile(program Program, analysis *Analysis) (Bytecode, error) {
	expected, err := Analyze(program)
	if err != nil {
		return Bytecode{}, languageError(StageCompile, CodeInvalidInput, errorPosition(err), "program is not a valid analyzed AST")
	}
	if analysis == nil || analysis.Slots == nil || analysis.SlotCount != expected.SlotCount || len(analysis.Slots) != len(expected.Slots) {
		return Bytecode{}, languageError(StageCompile, CodeInvalidInput, program.Span.Start, "analysis shape does not match program")
	}
	for name, expectedSlot := range expected.Slots {
		if actualSlot, exists := analysis.Slots[name]; !exists || actualSlot != expectedSlot {
			return Bytecode{}, languageError(StageCompile, CodeInvalidInput, program.Span.Start, "analysis slots do not match program")
		}
	}

	instructions := make([]Instruction, 0)
	for i := range program.Statements {
		statement := &program.Statements[i]
		if err := compileExpression(statement.Expr, analysis, &instructions); err != nil {
			return Bytecode{}, err
		}
		switch statement.Kind {
		case StmtLet:
			instructions = append(instructions, Instruction{
				Op: OpStore, Operand: int64(analysis.Slots[statement.Name]), Span: statement.Span,
			})
		case StmtPrint:
			instructions = append(instructions, Instruction{Op: OpPrint, Span: statement.Span})
		case StmtExpr:
			instructions = append(instructions, Instruction{Op: OpPop, Span: statement.Span})
		default:
			return Bytecode{}, languageError(StageCompile, CodeInvalidInput, statement.Span.Start, "unknown statement kind")
		}
	}
	instructions = append(instructions, Instruction{Op: OpHalt, Span: program.Span})
	return Bytecode{Instructions: instructions, SlotCount: analysis.SlotCount}, nil
}

func compileExpression(expr *Expr, analysis *Analysis, instructions *[]Instruction) error {
	switch expr.Kind {
	case ExprInteger:
		*instructions = append(*instructions, Instruction{Op: OpPush, Operand: expr.Integer, Span: expr.Span})
	case ExprName:
		slot, exists := analysis.Slots[expr.Name]
		if !exists {
			return languageError(StageCompile, CodeInvalidInput, expr.Span.Start, "name has no analyzed slot")
		}
		*instructions = append(*instructions, Instruction{Op: OpLoad, Operand: int64(slot), Span: expr.Span})
	case ExprBinary:
		if err := compileExpression(expr.Left, analysis, instructions); err != nil {
			return err
		}
		if err := compileExpression(expr.Right, analysis, instructions); err != nil {
			return err
		}
		op := OpInvalid
		switch expr.Op {
		case TokenPlus:
			op = OpAdd
		case TokenMinus:
			op = OpSub
		case TokenStar:
			op = OpMul
		case TokenSlash:
			op = OpDiv
		default:
			return languageError(StageCompile, CodeInvalidInput, expr.Span.Start, "unknown binary operator")
		}
		*instructions = append(*instructions, Instruction{Op: op, Span: expr.Span})
	default:
		return languageError(StageCompile, CodeInvalidInput, expr.Span.Start, "unknown expression kind")
	}
	return nil
}

func errorPosition(err error) Position {
	if languageErr, ok := err.(*Error); ok {
		return languageErr.Pos
	}
	return Position{Line: 1, Column: 1}
}

func Build(source string) (Bytecode, error) {
	tokens, err := Scan(source)
	if err != nil {
		return Bytecode{}, err
	}
	program, err := Parse(tokens)
	if err != nil {
		return Bytecode{}, err
	}
	analysis, err := Analyze(program)
	if err != nil {
		return Bytecode{}, err
	}
	return Compile(program, analysis)
}

func Execute(source string) ([]int64, error) {
	code, err := Build(source)
	if err != nil {
		return nil, err
	}
	return Run(code)
}
