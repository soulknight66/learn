"""Stateful tree-walking Pebble interpreter."""

from collections.abc import Callable
from typing import Any

from .env import Environment
from .errors import ArityError, EvalError
from .reader import read_all
from .values import Builtin, Symbol, UserFunction, format_value


def is_falsey(value: Any) -> bool:
    return value is None or value is False


def _require_integer(value: Any, operation: str) -> int:
    if type(value) is not int:
        raise EvalError(f"{operation}: expected integer, received {format_value(value)}")
    return value


def _require_list_or_nil(value: Any, operation: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise EvalError(f"{operation}: expected list or nil, received {format_value(value)}")
    return value


def _data_equal(left: Any, right: Any) -> bool:
    pending = [(left, right)]
    while pending:
        current_left, current_right = pending.pop()
        if isinstance(current_left, (Builtin, UserFunction)) or isinstance(
            current_right, (Builtin, UserFunction)
        ):
            return False
        if type(current_left) is not type(current_right):
            return False
        if isinstance(current_left, list):
            if len(current_left) != len(current_right):
                return False
            pending.extend(zip(current_left, current_right))
        elif current_left != current_right:
            return False
    return True


class Interpreter:
    """A Pebble evaluator with persistent globals and a configurable output sink."""

    def __init__(self, output: Callable[[str], None] | None = None) -> None:
        self.output = output if output is not None else print
        self.globals = Environment()
        self._install_builtins()

    @staticmethod
    def _check_form_arity(name: str, arguments: list[Any], minimum: int, maximum: int) -> None:
        count = len(arguments)
        if count < minimum or count > maximum:
            expected = str(minimum) if minimum == maximum else f"{minimum} to {maximum}"
            raise ArityError(
                f"{name}: expected {expected} argument(s), received {count}"
            )

    def eval(self, form: Any, env: Environment | None = None) -> Any:
        """Evaluate a form, looping when the next form occupies tail position."""

        try:
            return self._eval(form, env)
        except RecursionError:
            raise EvalError("evaluation exceeded the host recursion budget") from None

    def _eval(self, form: Any, env: Environment | None = None) -> Any:
        """Internal evaluator; ``eval`` translates host stack exhaustion."""

        current = form
        scope = env if env is not None else self.globals

        while True:
            if isinstance(current, Symbol):
                return scope.lookup(current.name)
            if current is None or type(current) in (bool, int, str):
                return current
            if not isinstance(current, list):
                raise EvalError(f"cannot evaluate host value {type(current).__name__}")
            if not current:
                return []

            operator = current[0]
            arguments = current[1:]
            if isinstance(operator, Symbol):
                name = operator.name
                if name == "quote":
                    self._check_form_arity(name, arguments, 1, 1)
                    return arguments[0]
                if name == "if":
                    self._check_form_arity(name, arguments, 2, 3)
                    condition = self.eval(arguments[0], scope)
                    if is_falsey(condition):
                        if len(arguments) == 2:
                            return None
                        current = arguments[2]
                    else:
                        current = arguments[1]
                    continue
                if name == "do":
                    if not arguments:
                        return None
                    for expression in arguments[:-1]:
                        self.eval(expression, scope)
                    current = arguments[-1]
                    continue
                if name == "def":
                    self._check_form_arity(name, arguments, 2, 2)
                    target = arguments[0]
                    if not isinstance(target, Symbol):
                        raise EvalError("def: first argument must be a symbol")
                    value = self.eval(arguments[1], scope)
                    return self.globals.define(target.name, value)
                if name == "let":
                    if len(arguments) < 2:
                        raise ArityError(
                            f"let: expected bindings and at least one body form, received {len(arguments)} argument(s)"
                        )
                    bindings = arguments[0]
                    if not isinstance(bindings, list):
                        raise EvalError("let: bindings must be a list")
                    child = Environment(parent=scope)
                    for binding in bindings:
                        if (
                            not isinstance(binding, list)
                            or len(binding) != 2
                            or not isinstance(binding[0], Symbol)
                        ):
                            raise EvalError(
                                "let: each binding must be a two-item list beginning with a symbol"
                            )
                        child.define(binding[0].name, self.eval(binding[1], child))
                    for expression in arguments[1:-1]:
                        self.eval(expression, child)
                    scope = child
                    current = arguments[-1]
                    continue
                if name == "fn":
                    if len(arguments) < 2:
                        raise ArityError(
                            f"fn: expected parameters and at least one body form, received {len(arguments)} argument(s)"
                        )
                    parameters = arguments[0]
                    if not isinstance(parameters, list) or not all(
                        isinstance(item, Symbol) for item in parameters
                    ):
                        raise EvalError("fn: parameters must be a list of symbols")
                    names = tuple(item.name for item in parameters)
                    if len(names) != len(set(names)):
                        raise EvalError("fn: parameter names must be distinct")
                    return UserFunction(names, tuple(arguments[1:]), scope)

            callee = self.eval(operator, scope)
            evaluated = [self.eval(argument, scope) for argument in arguments]
            if isinstance(callee, Builtin):
                return callee.invoke(evaluated)
            if isinstance(callee, UserFunction):
                if len(evaluated) != len(callee.parameters):
                    raise ArityError(
                        f"fn: expected {len(callee.parameters)} argument(s), received {len(evaluated)}"
                    )
                call_scope = Environment(
                    parent=callee.closure,
                    initial=dict(zip(callee.parameters, evaluated)),
                )
                for expression in callee.body[:-1]:
                    self.eval(expression, call_scope)
                scope = call_scope
                current = callee.body[-1]
                continue
            raise EvalError(f"attempted to call non-function {format_value(callee)}")

    def eval_source(self, source: str) -> Any:
        result: Any = None
        for form in read_all(source):
            result = self.eval(form)
        return result

    def _install_builtins(self) -> None:
        def install(
            name: str,
            minimum: int,
            maximum: int | None,
            function: Callable[[list[Any]], Any],
        ) -> None:
            self.globals.define(name, Builtin(name, function, minimum, maximum))

        def add(arguments: list[Any]) -> int:
            return sum(_require_integer(item, "+") for item in arguments)

        def multiply(arguments: list[Any]) -> int:
            result = 1
            for item in arguments:
                result *= _require_integer(item, "*")
            return result

        def subtract(arguments: list[Any]) -> int:
            first = _require_integer(arguments[0], "-")
            if len(arguments) == 1:
                return -first
            result = first
            for item in arguments[1:]:
                result -= _require_integer(item, "-")
            return result

        def divide(arguments: list[Any]) -> int:
            dividend = _require_integer(arguments[0], "/")
            divisor = _require_integer(arguments[1], "/")
            if divisor == 0:
                raise EvalError("/: division by zero")
            magnitude = abs(dividend) // abs(divisor)
            return -magnitude if (dividend < 0) != (divisor < 0) else magnitude

        def compare(operation: str, predicate: Callable[[int, int], bool]):
            def implementation(arguments: list[Any]) -> bool:
                left = _require_integer(arguments[0], operation)
                right = _require_integer(arguments[1], operation)
                return predicate(left, right)

            return implementation

        def first(arguments: list[Any]) -> Any:
            values = _require_list_or_nil(arguments[0], "first")
            return values[0] if values else None

        def rest(arguments: list[Any]) -> list[Any]:
            values = _require_list_or_nil(arguments[0], "rest")
            return list(values[1:])

        def cons(arguments: list[Any]) -> list[Any]:
            tail = _require_list_or_nil(arguments[1], "cons")
            return [arguments[0], *tail]

        def count(arguments: list[Any]) -> int:
            value = arguments[0]
            if value is None:
                return 0
            if isinstance(value, (list, str)):
                return len(value)
            raise EvalError(f"count: expected list, string, or nil, received {format_value(value)}")

        def is_empty(arguments: list[Any]) -> bool:
            """Implement the total predicate defined by the public contract."""

            value = arguments[0]
            return value is None or (isinstance(value, list) and len(value) == 0)

        def concatenate(arguments: list[Any]) -> str:
            return "".join(
                item if isinstance(item, str) else format_value(item) for item in arguments
            )

        def emit(arguments: list[Any]) -> None:
            rendered = format_value(arguments[0])
            try:
                self.output(rendered)
            except Exception as error:
                raise EvalError("print: output sink failed") from error
            return None

        install("+", 0, None, add)
        install("*", 0, None, multiply)
        install("-", 1, None, subtract)
        install("/", 2, 2, divide)
        install("=", 2, 2, lambda values: _data_equal(values[0], values[1]))
        install("<", 2, 2, compare("<", lambda left, right: left < right))
        install("<=", 2, 2, compare("<=", lambda left, right: left <= right))
        install(">", 2, 2, compare(">", lambda left, right: left > right))
        install(">=", 2, 2, compare(">=", lambda left, right: left >= right))
        install("list", 0, None, lambda values: list(values))
        install("first", 1, 1, first)
        install("rest", 1, 1, rest)
        install("cons", 2, 2, cons)
        install("empty?", 1, 1, is_empty)
        install("count", 1, 1, count)
        install("not", 1, 1, lambda values: is_falsey(values[0]))
        install("pr-str", 1, 1, lambda values: format_value(values[0]))
        install("str", 0, None, concatenate)
        install("print", 1, 1, emit)
