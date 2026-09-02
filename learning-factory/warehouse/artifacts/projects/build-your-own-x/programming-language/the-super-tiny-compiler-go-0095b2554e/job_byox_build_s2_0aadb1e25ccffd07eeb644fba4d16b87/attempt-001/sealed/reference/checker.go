package prefixforge

func Check(program Program) ([]ValueType, error) {
	if len(program.Exprs) == 0 {
		return nil, stageError("check", program.At, "program has no expressions")
	}
	types := make([]ValueType, 0, len(program.Exprs))
	for _, expr := range program.Exprs {
		typ, err := checkExpr(expr, 0)
		if err != nil {
			return nil, err
		}
		types = append(types, typ)
	}
	return types, nil
}

func checkExpr(expr Expr, depth int) (ValueType, error) {
	switch n := expr.(type) {
	case NumberExpr:
		return TypeNumber, nil
	case *NumberExpr:
		if n == nil {
			return "", stageError("check", initialSpan(), "nil number expression")
		}
		return TypeNumber, nil
	case StringExpr:
		return TypeString, nil
	case *StringExpr:
		if n == nil {
			return "", stageError("check", initialSpan(), "nil string expression")
		}
		return TypeString, nil
	case BoolExpr:
		return TypeBoolean, nil
	case *BoolExpr:
		if n == nil {
			return "", stageError("check", initialSpan(), "nil boolean expression")
		}
		return TypeBoolean, nil
	case CallExpr:
		return checkCall(n, depth)
	case *CallExpr:
		if n == nil {
			return "", stageError("check", initialSpan(), "nil call expression")
		}
		return checkCall(*n, depth)
	case nil:
		return "", stageError("check", initialSpan(), "nil expression")
	default:
		return "", stageError("check", spanOf(expr), "unsupported expression node")
	}
}

func checkCall(call CallExpr, depth int) (ValueType, error) {
	if depth >= MaxNesting {
		return "", stageError("check", call.At, "call nesting exceeds %d", MaxNesting)
	}

	switch call.Name {
	case "add", "sub", "mul", "div", "lt":
		if err := requireArity(call, 2); err != nil {
			return "", err
		}
		for i := range call.Args {
			typ, err := checkExpr(call.Args[i], depth+1)
			if err != nil {
				return "", err
			}
			if typ != TypeNumber {
				return "", typeMismatch(call.Args[i], TypeNumber, typ)
			}
		}
		if call.Name == "lt" {
			return TypeBoolean, nil
		}
		return TypeNumber, nil

	case "concat":
		if err := requireArity(call, 2); err != nil {
			return "", err
		}
		for i := range call.Args {
			typ, err := checkExpr(call.Args[i], depth+1)
			if err != nil {
				return "", err
			}
			if typ != TypeString {
				return "", typeMismatch(call.Args[i], TypeString, typ)
			}
		}
		return TypeString, nil

	case "and", "or":
		if err := requireArity(call, 2); err != nil {
			return "", err
		}
		for i := range call.Args {
			typ, err := checkExpr(call.Args[i], depth+1)
			if err != nil {
				return "", err
			}
			if typ != TypeBoolean {
				return "", typeMismatch(call.Args[i], TypeBoolean, typ)
			}
		}
		return TypeBoolean, nil

	case "not":
		if err := requireArity(call, 1); err != nil {
			return "", err
		}
		typ, err := checkExpr(call.Args[0], depth+1)
		if err != nil {
			return "", err
		}
		if typ != TypeBoolean {
			return "", typeMismatch(call.Args[0], TypeBoolean, typ)
		}
		return TypeBoolean, nil

	case "eq":
		if err := requireArity(call, 2); err != nil {
			return "", err
		}
		left, err := checkExpr(call.Args[0], depth+1)
		if err != nil {
			return "", err
		}
		right, err := checkExpr(call.Args[1], depth+1)
		if err != nil {
			return "", err
		}
		if left != right {
			return "", stageError("check", spanOf(call.Args[1]), "eq arguments differ: %s and %s", left, right)
		}
		return TypeBoolean, nil

	case "if":
		if err := requireArity(call, 3); err != nil {
			return "", err
		}
		condition, err := checkExpr(call.Args[0], depth+1)
		if err != nil {
			return "", err
		}
		if condition != TypeBoolean {
			return "", typeMismatch(call.Args[0], TypeBoolean, condition)
		}
		thenType, err := checkExpr(call.Args[1], depth+1)
		if err != nil {
			return "", err
		}
		elseType, err := checkExpr(call.Args[2], depth+1)
		if err != nil {
			return "", err
		}
		if thenType != elseType {
			return "", stageError("check", spanOf(call.Args[2]), "if branches differ: %s and %s", thenType, elseType)
		}
		return thenType, nil

	case "print":
		if err := requireArity(call, 1); err != nil {
			return "", err
		}
		return checkExpr(call.Args[0], depth+1)

	default:
		at := call.NameSpan
		if at == (Span{}) {
			at = call.At
		}
		return "", stageError("check", at, "unknown built-in %q", call.Name)
	}
}

func requireArity(call CallExpr, want int) error {
	if len(call.Args) != want {
		return stageError("check", call.At, "%s expects %d arguments, got %d", call.Name, want, len(call.Args))
	}
	return nil
}

func typeMismatch(expr Expr, want, got ValueType) error {
	return stageError("check", spanOf(expr), "expected %s, got %s", want, got)
}
