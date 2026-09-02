# Code-review exercises

1. Review a VM that indexes constants before checking the operand type/range.
2. Review an environment whose assignment writes only to the current scope.
3. Review an `or` compiler that always compiles and evaluates its right operand.
4. Review a scanner that increments column by UTF-16 code point rather than Java `char` consumed.
5. Review a CLI that catches every `Exception` and labels it a parse error.

For each, identify contract impact, a minimal reproducer, a deterministic regression test, and the
smallest safe fix. Store solution-bearing notes only under this exercise's own sealed area.
