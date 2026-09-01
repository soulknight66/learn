# Code-review exercises

These are instructor-side review drills. Each directory contains a deliberately
small flawed implementation, a prompt, and an executable characterization.
Review the code before running the characterization so the observations do not
replace source analysis.

- `exercise-01`: route matching and request-local state
- `exercise-02`: response-helper API and HTTP framing

Every answer is confined to the corresponding exercise's `sealed/` directory.
The characterization scripts intentionally exit non-zero while the listed
defects remain; they are not tests of the main reference implementation.
