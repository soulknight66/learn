import io
import unittest

from minnow import run_source


def truncating_division(left, right):
    magnitude = abs(left) // abs(right)
    return -magnitude if (left < 0) != (right < 0) else magnitude


class GeneratedExpressionTests(unittest.TestCase):
    def test_deterministic_integer_matrix(self):
        values = (-20, -7, -1, 0, 1, 6, 19)
        lines = []
        expected = []
        for left in values:
            for right in values:
                for symbol, operation in (
                    ("+", lambda a, b: a + b),
                    ("-", lambda a, b: a - b),
                    ("*", lambda a, b: a * b),
                    ("==", lambda a, b: int(a == b)),
                    ("!=", lambda a, b: int(a != b)),
                    ("<", lambda a, b: int(a < b)),
                    ("<=", lambda a, b: int(a <= b)),
                    (">", lambda a, b: int(a > b)),
                    (">=", lambda a, b: int(a >= b)),
                ):
                    lines.append(f"print ({left}) {symbol} ({right});")
                    expected.append(operation(left, right))
                if right != 0:
                    quotient = truncating_division(left, right)
                    lines.append(f"print ({left}) / ({right});")
                    expected.append(quotient)
                    lines.append(f"print ({left}) % ({right});")
                    expected.append(left - quotient * right)

        output = io.StringIO()
        run_source("\n".join(lines), output)
        actual = [int(line) for line in output.getvalue().splitlines()]
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
