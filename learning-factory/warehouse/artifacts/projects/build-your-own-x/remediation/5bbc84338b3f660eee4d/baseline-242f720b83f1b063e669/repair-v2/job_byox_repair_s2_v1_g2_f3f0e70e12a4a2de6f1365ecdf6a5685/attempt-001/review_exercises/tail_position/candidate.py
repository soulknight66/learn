"""Review candidate; language tail positions still recurse through the host."""


class FormArityError(Exception):
    """The fragment received the wrong special-form shape."""


def evaluate_special(name, arguments, environment, evaluate):
    if name == "if":
        if len(arguments) not in (2, 3):
            raise FormArityError("if expects two or three arguments")
        condition = evaluate(arguments[0], environment)
        if condition is None or condition is False:
            if len(arguments) == 2:
                return None
            branch = arguments[2]
        else:
            branch = arguments[1]
        return evaluate(branch, environment)
    if name == "do":
        if not arguments:
            return None
        for expression in arguments[:-1]:
            evaluate(expression, environment)
        return evaluate(arguments[-1], environment)
    raise LookupError(name)
