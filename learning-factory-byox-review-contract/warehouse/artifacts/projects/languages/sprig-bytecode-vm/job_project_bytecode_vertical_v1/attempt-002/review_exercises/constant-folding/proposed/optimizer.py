from __future__ import annotations

from tinyvm.model import Binary, Literal, Unary
from tinyvm.semantics import binary


def fold(expression):
    if isinstance(expression, Literal):
        return expression
    if isinstance(expression, Unary):
        right = fold(expression.right)
        if isinstance(right, Literal):
            return Literal(-right.value if expression.operator == "-" else int(right.value == 0))
        return Unary(expression.operator, right)
    if isinstance(expression, Binary):
        left = fold(expression.left)
        right = fold(expression.right)
        if isinstance(left, Literal) and isinstance(right, Literal):
            if expression.operator == "&&": return Literal(int(left.value != 0 and right.value != 0))
            if expression.operator == "||": return Literal(int(left.value != 0 or right.value != 0))
            return Literal(binary(expression.operator, left.value, right.value))
        return Binary(left, expression.operator, right)
    return expression
