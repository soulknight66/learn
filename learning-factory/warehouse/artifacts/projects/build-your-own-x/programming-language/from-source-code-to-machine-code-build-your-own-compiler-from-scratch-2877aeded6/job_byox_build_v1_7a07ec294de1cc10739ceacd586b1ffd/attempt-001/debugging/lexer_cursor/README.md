# Exercise: the wandering lexer cursor

`buggy.py` is intended to consume one logical newline and return `(new_index, new_line, new_column)`.
It passes for `"\n"` in the middle of a buffer but fails at EOF and mishandles some CR cases.

1. Identify every input that can index outside the string.
2. State the invariant connecting `index` and the next unread character.
3. Repair CR, LF, and CRLF behavior without counting CRLF twice.
4. Write a table-driven test that includes empty suffixes.
