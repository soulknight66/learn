"""Stack virtual machine (milestone 4)."""


class VirtualMachine(object):
    def __init__(self, max_steps=10000):
        self.max_steps = max_steps

    def run(self, bytecode, env=None):
        raise NotImplementedError("milestone 4: VirtualMachine.run")
