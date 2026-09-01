"""Runtime value classes.

Milestone 1: finish data equality/repr decisions without making symbols host strings.
"""


class Symbol(object):
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Symbol) and self.name == other.name

    def __hash__(self):
        return hash((Symbol, self.name))

    def __repr__(self):
        return "Symbol({0!r})".format(self.name)


class UserFunction(object):
    def __init__(self, parameters, body, closure):
        self.parameters = parameters
        self.body = body
        self.closure = closure
