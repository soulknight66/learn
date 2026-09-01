"""Lexical environments and total, checked builtin operations."""

from .errors import LanguageError
from .values import Symbol, UserFunction


def _binding_name(name):
    if isinstance(name, Symbol):
        return name.name
    if isinstance(name, str):
        return name
    raise LanguageError("NAME_INVALID", "binding name must be a symbol")


class Environment(object):
    __slots__ = ("parent", "bindings")

    def __init__(self, parent=None):
        if parent is not None and not isinstance(parent, Environment):
            raise LanguageError("ENV_PARENT", "environment parent must be an environment")
        self.parent = parent
        self.bindings = {}

    def define(self, name, value):
        self.bindings[_binding_name(name)] = value
        return value

    def _find(self, name):
        key = _binding_name(name)
        environment = self
        while environment is not None:
            if key in environment.bindings:
                return environment, key
            environment = environment.parent
        return None, key

    def get(self, name):
        environment, key = self._find(name)
        if environment is None:
            raise LanguageError("NAME_UNBOUND", "unbound name: {0}".format(key))
        return environment.bindings[key]

    def assign(self, name, value):
        environment, key = self._find(name)
        if environment is None:
            raise LanguageError("NAME_UNBOUND", "unbound name: {0}".format(key))
        environment.bindings[key] = value
        return value


class Builtin(object):
    _sprig_builtin = True
    __slots__ = ("name", "function")

    def __init__(self, name, function):
        self.name = name
        self.function = function

    def invoke(self, arguments):
        try:
            return self.function(arguments)
        except LanguageError:
            raise
        except Exception as error:
            raise LanguageError(
                "BUILTIN_FAILURE",
                "builtin {0} failed safely: {1}".format(self.name, type(error).__name__),
            )

    def __repr__(self):
        return "<Builtin {0}>".format(self.name)


def is_truthy(value):
    return value is not None and value is not False


def structural_equal(left, right):
    if left is None or right is None:
        return left is right
    if type(left) is bool or type(right) is bool:
        return type(left) is bool and type(right) is bool and left is right
    if type(left) is int or type(right) is int:
        return type(left) is int and type(right) is int and left == right
    if isinstance(left, Symbol) or isinstance(right, Symbol):
        return isinstance(left, Symbol) and isinstance(right, Symbol) and left.name == right.name
    if isinstance(left, str) or isinstance(right, str):
        return isinstance(left, str) and isinstance(right, str) and left == right
    if isinstance(left, list) or isinstance(right, list):
        if not isinstance(left, list) or not isinstance(right, list):
            return False
        return len(left) == len(right) and all(
            structural_equal(a, b) for a, b in zip(left, right)
        )
    if isinstance(left, (Builtin, UserFunction)) or isinstance(right, (Builtin, UserFunction)):
        return left is right
    return left is right


def _arity(arguments, minimum, maximum=None):
    count = len(arguments)
    if count < minimum or (maximum is not None and count > maximum):
        if maximum is None:
            expected = "at least {0}".format(minimum)
        elif minimum == maximum:
            expected = str(minimum)
        else:
            expected = "{0} to {1}".format(minimum, maximum)
        raise LanguageError(
            "BUILTIN_ARITY", "expected {0} argument(s), received {1}".format(expected, count)
        )


def _integers(arguments):
    for value in arguments:
        if type(value) is not int:
            raise LanguageError("BUILTIN_TYPE", "expected integer arguments")


def _list(value):
    if not isinstance(value, list):
        raise LanguageError("BUILTIN_TYPE", "expected a list")
    return value


def _add(arguments):
    _integers(arguments)
    total = 0
    for value in arguments:
        total += value
    return total


def _subtract(arguments):
    _arity(arguments, 1)
    _integers(arguments)
    if len(arguments) == 1:
        return -arguments[0]
    result = arguments[0]
    for value in arguments[1:]:
        result -= value
    return result


def _multiply(arguments):
    _integers(arguments)
    result = 1
    for value in arguments:
        result *= value
    return result


def _truncate_division(left, right):
    if right == 0:
        raise LanguageError("BUILTIN_DIV_ZERO", "division by zero")
    quotient = abs(left) // abs(right)
    if (left < 0) != (right < 0):
        quotient = -quotient
    return quotient


def _divide(arguments):
    _arity(arguments, 2)
    _integers(arguments)
    result = arguments[0]
    for value in arguments[1:]:
        result = _truncate_division(result, value)
    return result


def _comparison(operator):
    def compare(arguments):
        _arity(arguments, 2)
        _integers(arguments)
        return all(operator(a, b) for a, b in zip(arguments, arguments[1:]))
    return compare


def _equal(arguments):
    _arity(arguments, 2, 2)
    return structural_equal(arguments[0], arguments[1])


def _make_list(arguments):
    return list(arguments)


def _head(arguments):
    _arity(arguments, 1, 1)
    value = _list(arguments[0])
    return value[0] if value else None


def _tail(arguments):
    _arity(arguments, 1, 1)
    value = _list(arguments[0])
    return list(value[1:])


def _cons(arguments):
    _arity(arguments, 2, 2)
    value = _list(arguments[1])
    return [arguments[0]] + list(value)


def _empty(arguments):
    _arity(arguments, 1, 1)
    return len(_list(arguments[0])) == 0


def _count(arguments):
    _arity(arguments, 1, 1)
    return len(_list(arguments[0]))


def _not(arguments):
    _arity(arguments, 1, 1)
    return not is_truthy(arguments[0])


def _type(arguments):
    _arity(arguments, 1, 1)
    value = arguments[0]
    if value is None:
        name = "nil"
    elif type(value) is bool:
        name = "boolean"
    elif type(value) is int:
        name = "integer"
    elif isinstance(value, str):
        name = "string"
    elif isinstance(value, Symbol):
        name = "symbol"
    elif isinstance(value, list):
        name = "list"
    elif isinstance(value, Builtin):
        name = "builtin"
    elif isinstance(value, UserFunction):
        name = "function"
    else:
        raise LanguageError("BUILTIN_TYPE", "unknown host value")
    return Symbol(name)


def default_environment():
    import operator

    operations = {
        "+": _add,
        "-": _subtract,
        "*": _multiply,
        "/": _divide,
        "<": _comparison(operator.lt),
        "<=": _comparison(operator.le),
        ">": _comparison(operator.gt),
        ">=": _comparison(operator.ge),
        "=": _equal,
        "list": _make_list,
        "head": _head,
        "tail": _tail,
        "cons": _cons,
        "empty?": _empty,
        "count": _count,
        "not": _not,
        "type": _type,
    }
    environment = Environment()
    for name in sorted(operations):
        environment.define(name, Builtin(name, operations[name]))
    return environment
