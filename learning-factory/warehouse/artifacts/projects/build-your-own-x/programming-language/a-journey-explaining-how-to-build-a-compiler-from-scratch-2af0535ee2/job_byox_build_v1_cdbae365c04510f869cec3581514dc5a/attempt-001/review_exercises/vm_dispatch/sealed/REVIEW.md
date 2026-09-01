# Review answer

Critical: both pre-decrements can wrap size_t and index outside the stack when depth is below two.
Check depth at least two before either decrement. Prefer reading the two operands, validating the
operation, then committing the new depth and result together.

Critical: signed addition overflows with undefined C behavior. Before evaluating it, reject a positive
right operand when left exceeds INT64_MAX-right, and reject a negative right operand when left is below
INT64_MIN-right.

Moderate: the budget function mutates steps before deciding. With steps already UINT64_MAX it wraps to
zero, and callers can also struggle to define whether maximum zero permits work. Check steps greater
than or equal to maximum first; only increment when dispatch is permitted. The public reference treats
one permitted dispatch as one consumed unit.

The fragment also lacks stack-capacity and output-position context, so it should not be promoted into a
real dispatcher without an explicit VM state object and deterministic diagnostic path.
