# Incident: a harmless parser cleanup changed subtraction

Users report that chained subtraction produces a surprising value, while addition and simple
two-operand subtraction still pass. Work only from `buggy`, this report, and `regression.py`.
Explain the grammar invariant, minimize the failure, repair it, and add tests covering other
operators at the same precedence. Reveal the sealed root cause only after your postmortem.
