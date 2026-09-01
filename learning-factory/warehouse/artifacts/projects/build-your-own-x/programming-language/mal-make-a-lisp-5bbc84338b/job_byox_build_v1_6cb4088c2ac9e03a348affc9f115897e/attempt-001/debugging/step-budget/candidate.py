class BudgetExceeded(Exception):
    code = "STEP_LIMIT"


class Budget(object):
    def __init__(self, limit):
        self.limit = limit
        self.used = 0

    def consume(self):
        self.used += 1
        if self.used >= self.limit:
            raise BudgetExceeded()
