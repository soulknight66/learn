"""Budgeted tree-walking evaluator with lexical closures."""

from .errors import LanguageError
from .runtime import Builtin, Environment, is_truthy
from .values import Symbol, UserFunction


class Evaluator(object):
    def __init__(self, max_steps=10000, max_call_depth=200):
        if type(max_steps) is not int or max_steps < 0:
            raise ValueError("max_steps must be a non-negative integer")
        if type(max_call_depth) is not int or max_call_depth < 0:
            raise ValueError("max_call_depth must be a non-negative integer")
        self.max_steps = max_steps
        self.max_call_depth = max_call_depth
        self._steps = 0
        self._call_depth = 0

    def evaluate(self, form, env):
        if not isinstance(env, Environment):
            raise LanguageError("EVAL_ENV", "evaluation requires an environment")
        self._steps = 0
        self._call_depth = 0
        try:
            return self._eval(form, env)
        except RecursionError:
            raise LanguageError("EVAL_CALL_DEPTH", "host recursion boundary reached safely")

    def _step(self):
        self._steps += 1
        if self._steps > self.max_steps:
            raise LanguageError("EVAL_STEP_LIMIT", "evaluation step limit exceeded")

    @staticmethod
    def _form_error(message):
        raise LanguageError("EVAL_FORM", message)

    @staticmethod
    def _validated_names(values, label):
        if not isinstance(values, list):
            raise LanguageError("EVAL_FORM", "{0} must be a list".format(label))
        names = []
        seen = set()
        for value in values:
            if not isinstance(value, Symbol):
                raise LanguageError("EVAL_FORM", "{0} must contain symbols".format(label))
            if value.name in seen:
                raise LanguageError("EVAL_FORM", "duplicate name in {0}: {1}".format(label, value.name))
            seen.add(value.name)
            names.append(value)
        return names

    def _eval(self, form, env):
        self._step()
        if isinstance(form, Symbol):
            return env.get(form)
        if not isinstance(form, list):
            return form
        if not form:
            return []

        head = form[0]
        special = head.name if isinstance(head, Symbol) else None

        if special == "quote":
            if len(form) != 2:
                self._form_error("quote expects one form")
            return form[1]

        if special == "if":
            if len(form) not in (3, 4):
                self._form_error("if expects condition, then, and optional else")
            condition = self._eval(form[1], env)
            if is_truthy(condition):
                return self._eval(form[2], env)
            if len(form) == 4:
                return self._eval(form[3], env)
            return None

        if special == "do":
            result = None
            for child in form[1:]:
                result = self._eval(child, env)
            return result

        if special == "let":
            if len(form) < 3 or not isinstance(form[1], list):
                self._form_error("let expects a binding list and body")
            pairs = form[1]
            names = []
            seen = set()
            for pair in pairs:
                if not isinstance(pair, list) or len(pair) != 2 or not isinstance(pair[0], Symbol):
                    self._form_error("each let binding must be (name initializer)")
                if pair[0].name in seen:
                    self._form_error("duplicate let binding: {0}".format(pair[0].name))
                seen.add(pair[0].name)
                names.append(pair[0])
            child_env = Environment(env)
            for pair, name in zip(pairs, names):
                child_env.define(name, self._eval(pair[1], child_env))
            result = None
            for child in form[2:]:
                result = self._eval(child, child_env)
            return result

        if special == "fn":
            if len(form) < 3:
                self._form_error("fn expects parameters and at least one body form")
            parameters = self._validated_names(form[1], "parameter list")
            return UserFunction(parameters, form[2:], env)

        if special == "def":
            if len(form) != 3 or not isinstance(form[1], Symbol):
                self._form_error("def expects a name and value")
            value = self._eval(form[2], env)
            return env.define(form[1], value)

        if special == "set!":
            if len(form) != 3 or not isinstance(form[1], Symbol):
                self._form_error("set! expects a name and value")
            value = self._eval(form[2], env)
            return env.assign(form[1], value)

        if special == "and":
            result = True
            for child in form[1:]:
                result = self._eval(child, env)
                if not is_truthy(result):
                    return result
            return result

        if special == "or":
            result = None
            for child in form[1:]:
                result = self._eval(child, env)
                if is_truthy(result):
                    return result
            return result

        procedure = self._eval(head, env)
        arguments = []
        for child in form[1:]:
            arguments.append(self._eval(child, env))
        return self._apply(procedure, arguments)

    def _apply(self, procedure, arguments):
        self._step()
        if isinstance(procedure, Builtin):
            return procedure.invoke(arguments)
        if not isinstance(procedure, UserFunction):
            raise LanguageError("EVAL_NOT_CALLABLE", "attempted to call a non-callable value")
        if len(arguments) != len(procedure.parameters):
            raise LanguageError(
                "EVAL_ARITY", "expected {0} argument(s), received {1}".format(
                    len(procedure.parameters), len(arguments)
                )
            )
        if self._call_depth >= self.max_call_depth:
            raise LanguageError("EVAL_CALL_DEPTH", "function call-depth limit exceeded")
        self._call_depth += 1
        try:
            call_env = Environment(procedure.closure)
            for parameter, argument in zip(procedure.parameters, arguments):
                call_env.define(parameter, argument)
            result = None
            for child in procedure.body:
                result = self._eval(child, call_env)
            return result
        finally:
            self._call_depth -= 1
