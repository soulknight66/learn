# Debugging exercise: a check that happens too late

`buggy_checked_add.c` is a reduced arithmetic helper from a hypothetical VM. Review it without running undefined-behavior sanitizers first.

1. Identify the input pairs for which the function has undefined behavior.
2. Explain why the apparent range check cannot repair what already happened.
3. Rewrite the check so no overflowing expression is evaluated.
4. List boundary tests for positive and negative operands.

The maintainer answer is confined to this exercise’s `sealed/` directory.
