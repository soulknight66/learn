package prefixforge

import (
	"fmt"
	"io"
)

type evaluator struct {
	out   io.Writer
	steps int
}

func Evaluate(program Program, out io.Writer) (Value, error) {
	if _, err := Check(program); err != nil {
		return Value{}, err
	}
	if out == nil {
		out = io.Discard
	}
	e := &evaluator{out: out}
	var result Value
	for _, expr := range program.Exprs {
		value, err := e.evalExpr(expr, 0)
		if err != nil {
			return Value{}, err
		}
		result = value
	}
	return result, nil
}

func (e *evaluator) evalExpr(expr Expr, depth int) (Value, error) {
	if e.steps >= MaxSteps {
		return Value{}, stageError("eval", spanOf(expr), "evaluation exceeds %d steps", MaxSteps)
	}
	e.steps++
	switch n := expr.(type) {
	case NumberExpr:
		return NumberValue(n.Value), nil
	case *NumberExpr:
		if n == nil {
			return Value{}, stageError("eval", initialSpan(), "nil number expression")
		}
		return NumberValue(n.Value), nil
	case StringExpr:
		return StringValue(n.Value), nil
	case *StringExpr:
		if n == nil {
			return Value{}, stageError("eval", initialSpan(), "nil string expression")
		}
		return StringValue(n.Value), nil
	case BoolExpr:
		return BoolValue(n.Value), nil
	case *BoolExpr:
		if n == nil {
			return Value{}, stageError("eval", initialSpan(), "nil boolean expression")
		}
		return BoolValue(n.Value), nil
	case CallExpr:
		return e.evalCall(n, depth)
	case *CallExpr:
		if n == nil {
			return Value{}, stageError("eval", initialSpan(), "nil call expression")
		}
		return e.evalCall(*n, depth)
	default:
		return Value{}, stageError("eval", spanOf(expr), "unsupported expression node")
	}
}

func (e *evaluator) evalCall(call CallExpr, depth int) (Value, error) {
	if depth >= MaxNesting {
		return Value{}, stageError("eval", call.At, "call nesting exceeds %d", MaxNesting)
	}
	switch call.Name {
	case "if":
		condition, err := e.evalExpr(call.Args[0], depth+1)
		if err != nil {
			return Value{}, err
		}
		branch := 2
		if condition.Boolean {
			branch = 1
		}
		return e.evalExpr(call.Args[branch], depth+1)
	case "and":
		left, err := e.evalExpr(call.Args[0], depth+1)
		if err != nil {
			return Value{}, err
		}
		if !left.Boolean {
			return BoolValue(false), nil
		}
		return e.evalExpr(call.Args[1], depth+1)
	case "or":
		left, err := e.evalExpr(call.Args[0], depth+1)
		if err != nil {
			return Value{}, err
		}
		if left.Boolean {
			return BoolValue(true), nil
		}
		return e.evalExpr(call.Args[1], depth+1)
	case "print":
		value, err := e.evalExpr(call.Args[0], depth+1)
		if err != nil {
			return Value{}, err
		}
		if _, err := fmt.Fprintln(e.out, value.String()); err != nil {
			return Value{}, stageError("eval", call.At, "write output: %v", err)
		}
		return value, nil
	}

	left, err := e.evalExpr(call.Args[0], depth+1)
	if err != nil {
		return Value{}, err
	}
	if call.Name == "not" {
		return BoolValue(!left.Boolean), nil
	}
	right, err := e.evalExpr(call.Args[1], depth+1)
	if err != nil {
		return Value{}, err
	}
	switch call.Name {
	case "add", "sub", "mul", "div":
		op, _ := eagerOpcode(call.Name)
		result, problem := checkedArithmetic(op, left.Number, right.Number)
		if problem != "" {
			return Value{}, stageError("eval", call.At, "%s", problem)
		}
		return NumberValue(result), nil
	case "lt":
		return BoolValue(left.Number < right.Number), nil
	case "eq":
		return BoolValue(equalValues(left, right)), nil
	case "concat":
		return StringValue(left.Text + right.Text), nil
	default:
		return Value{}, stageError("eval", call.At, "unknown built-in %q", call.Name)
	}
}
