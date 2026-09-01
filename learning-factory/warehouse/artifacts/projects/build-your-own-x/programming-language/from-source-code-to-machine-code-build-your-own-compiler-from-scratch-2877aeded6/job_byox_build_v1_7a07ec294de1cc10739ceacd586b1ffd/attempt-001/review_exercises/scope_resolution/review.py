class Resolver:
    def __init__(self):
        self.locals = {}

    def declare(self, name, slot):
        self.locals[name] = slot

    def leave_block(self, names_declared_in_block):
        for name in names_declared_in_block:
            del self.locals[name]

    def resolve(self, name):
        return self.locals[name]
