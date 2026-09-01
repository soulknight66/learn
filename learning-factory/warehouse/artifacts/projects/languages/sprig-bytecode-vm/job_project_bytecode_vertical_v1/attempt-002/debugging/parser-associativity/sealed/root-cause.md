# Root cause

The term parser consumed its right operand by recursively parsing another complete term.
That changed `a-b-c` from `(a-b)-c` to `a-(b-c)`: right associativity hidden inside a small
refactor. Parse one factor per loop iteration to preserve the grammar's left fold. The correct
and buggy packages otherwise have identical parser text, as the integrity validator proves.
