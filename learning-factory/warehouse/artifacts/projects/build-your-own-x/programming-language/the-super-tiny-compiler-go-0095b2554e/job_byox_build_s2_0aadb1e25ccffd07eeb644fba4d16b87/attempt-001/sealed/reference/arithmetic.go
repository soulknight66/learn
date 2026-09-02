package prefixforge

import (
	"math"
)

func checkedArithmetic(op OpCode, left, right int64) (int64, string) {
	switch op {
	case OpAdd:
		if (right > 0 && left > math.MaxInt64-right) || (right < 0 && left < math.MinInt64-right) {
			return 0, "integer overflow in add"
		}
		return left + right, ""
	case OpSub:
		if (right > 0 && left < math.MinInt64+right) || (right < 0 && left > math.MaxInt64+right) {
			return 0, "integer overflow in sub"
		}
		return left - right, ""
	case OpMul:
		if left == 0 || right == 0 {
			return 0, ""
		}
		if (left == -1 && right == math.MinInt64) || (right == -1 && left == math.MinInt64) {
			return 0, "integer overflow in mul"
		}
		result := left * right
		if result/right != left {
			return 0, "integer overflow in mul"
		}
		return result, ""
	case OpDiv:
		if right == 0 {
			return 0, "division by zero"
		}
		if left == math.MinInt64 && right == -1 {
			return 0, "integer overflow in div"
		}
		return left / right, ""
	default:
		return 0, "unknown arithmetic operation"
	}
}
