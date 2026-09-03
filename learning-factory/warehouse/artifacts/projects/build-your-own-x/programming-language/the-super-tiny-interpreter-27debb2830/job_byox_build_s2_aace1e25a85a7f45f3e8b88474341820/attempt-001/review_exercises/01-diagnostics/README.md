# Review: diagnostic simplification

A patch catches every error in `execute` and throws `new Error("program failed")`. Review the patch
as if backend parity tests still compare successful results. List observable contracts it breaks,
cases it masks, and a safer boundary for formatting human-facing error text.
