# Reproducible investigation

`20 - 5` establishes basic subtraction; `20 - 5 - 3` distinguishes left and right grouping.
Inspecting the AST shows a `Binary(20, '-', Binary(5, '-', 3))`. Comparing precedence loops
isolates one operand-parser call. The regression passes against `sealed/fixed` and fails with
exit 1 against `buggy`; the patch changes only that call.
