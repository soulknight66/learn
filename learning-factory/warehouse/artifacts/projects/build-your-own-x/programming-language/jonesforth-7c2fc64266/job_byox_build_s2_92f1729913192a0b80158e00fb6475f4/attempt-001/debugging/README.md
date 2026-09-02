# Debugging exercises

These exercises reveal symptoms in stages. Diagnose each with a minimal input, state the broken
invariant, and propose a regression test before changing code.

## 1. Comparisons are consistently reversed

A draft interpreter prints false for `2 3 <` and true for `2 3 >`; equality still appears plausible
for some inputs. Inspect where `cmp` flags are created and every instruction between that point and
`setcc`. Remember that dispatch comparisons also modify flags.

## 2. A nested `else` runs the wrong body

Simple `if ... then` works, but the outer false branch of a nested conditional starts after the first
instruction in its else body. Draw the emitted cells and annotate whether each placeholder should be
patched before or after emitting the unconditional jump and its operand.

Evaluator answers are isolated under the corresponding exercise directories in `sealed/debugging/`.
