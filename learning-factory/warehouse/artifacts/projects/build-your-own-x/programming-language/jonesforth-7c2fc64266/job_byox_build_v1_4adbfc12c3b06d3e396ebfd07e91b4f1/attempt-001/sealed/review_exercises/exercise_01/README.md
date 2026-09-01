# Review exercise 01: signed division

Review this proposed VM handler:

    pop divisor
    pop dividend
    test divisor, divisor
    jz division_by_zero
    cqo
    idiv divisor
    push quotient

Identify contract violations and state the checks and mutation order needed before idiv. Consider
stack depths zero and one as well as signed 64-bit boundary operands.

