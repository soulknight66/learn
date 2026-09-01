"""Environments and builtins (milestone 2)."""


class Environment(object):
    def __init__(self, parent=None):
        self.parent = parent
        self.bindings = {}

    def define(self, name, value):
        raise NotImplementedError("milestone 2: Environment.define")

    def get(self, name):
        raise NotImplementedError("milestone 2: Environment.get")

    def assign(self, name, value):
        raise NotImplementedError("milestone 2: Environment.assign")


class Builtin(object):
    def __init__(self, name, function):
        self.name = name
        self.function = function

    def invoke(self, arguments):
        raise NotImplementedError("milestone 2: Builtin.invoke")


def default_environment():
    raise NotImplementedError("milestone 2: default_environment")
