# Adversarial test inventory

This inventory is for harness-controlled validation, not a claim that fuzzing was performed.

Exercise these classes with bounded subprocess time and captured output:

- empty, one-byte, embedded-NUL, maximum-size, and one-byte-oversize inputs;
- maximal identifiers, one-byte-oversize identifiers, keyword prefixes, and high-bit bytes;
- comment terminators at end of file and long runs of `/` and `*`;
- decimal values at and beyond `INT64_MAX`;
- long unary/operator chains, parentheses, blocks, declarations, arguments, and functions;
- every malformed delimiter and dangling `else` arrangement;
- duplicate symbols, missing symbols, wrong arities, and forward recursion;
- all arithmetic boundaries and zero divisors;
- value-stack growth from nested expressions, frame growth from recursion, and tiny step budgets;
- output followed by runtime failure, to verify documented non-transactional stdout behavior.

Generate cases without importing external corpora of uncertain provenance. A validator should record
the seed/generator version, exact executable digest, resource limits, and complete failing input.
