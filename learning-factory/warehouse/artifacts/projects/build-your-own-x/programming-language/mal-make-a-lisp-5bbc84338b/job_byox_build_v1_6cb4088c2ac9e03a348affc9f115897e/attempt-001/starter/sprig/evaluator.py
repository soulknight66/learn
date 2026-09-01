"""Tree-walking evaluator (milestones 2 and 3)."""


class Evaluator(object):
    def __init__(self, max_steps=10000, max_call_depth=200):
        self.max_steps = max_steps
        self.max_call_depth = max_call_depth

    def evaluate(self, form, env):
        """Evaluate one form with a fresh deterministic budget."""
        raise NotImplementedError("milestones 2-3: Evaluator.evaluate")
