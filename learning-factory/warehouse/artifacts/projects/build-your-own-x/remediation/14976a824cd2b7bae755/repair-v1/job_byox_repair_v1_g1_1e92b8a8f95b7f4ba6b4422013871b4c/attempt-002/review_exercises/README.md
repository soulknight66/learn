# Code-review exercises

These exercises practice reviewing security- and lifecycle-sensitive shell
code without executing it. For each candidate, write findings that include:

- the triggering input or interleaving;
- the resulting impact;
- a concrete remediation; and
- a severity justified by this educational runtime's trust boundary.

Start with correctness and containment issues before style. Do not run the
candidate snippets as root; they are intentionally unsafe. Model reviews are
kept in the `sealed/` directory belonging to each exercise.

