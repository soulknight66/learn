from __future__ import annotations

from .model import RuntimeFault


INT_MIN = -(2 ** 63)
INT_MAX = 2 ** 63 - 1


def checked(value: int) -> int:
    if value < INT_MIN or value > INT_MAX:
        raise RuntimeFault("signed 64-bit integer overflow")
    return value


def truth(value: int) -> int:
    return int(value != 0)


def trunc_div(left: int, right: int) -> int:
    if right == 0:
        raise RuntimeFault("division by zero")
    if left == INT_MIN and right == -1:
        raise RuntimeFault("signed 64-bit integer overflow")
    quotient = abs(left) // abs(right)
    return -quotient if (left < 0) != (right < 0) else quotient


def binary(operator: str, left: int, right: int) -> int:
    if operator == "+": return checked(left + right)
    if operator == "-": return checked(left - right)
    if operator == "*": return checked(left * right)
    if operator == "/": return trunc_div(left, right)
    if operator == "%": return left - trunc_div(left, right) * right
    if operator == "==": return int(left == right)
    if operator == "!=": return int(left != right)
    if operator == "<": return int(left < right)
    if operator == "<=": return int(left <= right)
    if operator == ">": return int(left > right)
    if operator == ">=": return int(left >= right)
    raise RuntimeFault(f"unknown binary operator: {operator}")
