"""Value classes that cannot be confused with host strings or callables."""


class Symbol(object):
    __slots__ = ("name",)

    def __init__(self, name):
        if not isinstance(name, str):
            raise TypeError("symbol name must be text")
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Symbol) and self.name == other.name

    def __hash__(self):
        return hash((Symbol, self.name))

    def __repr__(self):
        return "Symbol({0!r})".format(self.name)


class UserFunction(object):
    __slots__ = ("parameters", "body", "closure")

    def __init__(self, parameters, body, closure):
        self.parameters = tuple(parameters)
        self.body = tuple(body)
        self.closure = closure

    def __repr__(self):
        return "<UserFunction>"
