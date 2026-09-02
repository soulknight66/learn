"""Review candidate; the final expression still recurses through the host."""


def evaluate_special(name, arguments, environment, evaluate):
    if name == "if":
        branch = arguments[1] if evaluate(arguments[0], environment) else arguments[2]
        return evaluate(branch, environment)
    if name == "do":
        for expression in arguments[:-1]:
            evaluate(expression, environment)
        return evaluate(arguments[-1], environment)
    raise LookupError(name)
