# Debugging exercises

Use these symptom-only exercises after the corresponding public milestone works:

1. A newly mapped page sometimes exposes bytes written by a previous mapping.
2. Waking a blocked process eventually results in two processes marked running.
3. A failed oversized file write changes the file size.

Reproduce each defect with the smallest deterministic test, identify the violated invariant, and
propose a fix. Solution-bearing diagnoses are kept in `sealed/debugging/`, not here.
