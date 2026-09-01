# Exercise: scroll reads past the surface

Consider a `width * height` cell surface:

```c
for (row = 0; row < terminal->height; ++row) {
    for (column = 0; column < terminal->width; ++column) {
        cells[row * width + column] = cells[(row + 1) * width + column];
    }
}
blank_row(height - 1);
```

Visible output often looks correct in an emulator, but a guarded host test fails.

1. Compute the source index on the final iteration.
2. Rewrite the loop bounds as a safety invariant, not code.
3. Design a `2x2` test with distinct rows and guard values.
4. Explain why blanking afterward does not make the read safe.
