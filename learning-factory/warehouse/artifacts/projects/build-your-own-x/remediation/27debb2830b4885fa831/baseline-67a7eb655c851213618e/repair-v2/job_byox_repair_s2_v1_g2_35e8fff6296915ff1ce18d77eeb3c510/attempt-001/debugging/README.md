# Debugging exercises

Each exercise describes a symptom without disclosing its diagnosis. Its answer is kept in that
exercise's own `sealed/` directory.

- `01-scope-lifetime`: a nested block appears to erase or leak state.
- `02-jump-target`: one conditional path leaves the VM with the wrong result stack.

Use the smallest reproducer, write down the expected state transition, and add a regression test
before changing code.
