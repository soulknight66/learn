# Exercise 2 answer

For a signal-terminated process there is no ordinary exit code. Shell-compatible reporting uses
`128 + signal`, so SIGTERM (15) maps to 143 and SIGKILL (9) maps to 137. Returning the raw signal
number makes callers misclassify the result and disagrees with the runtime requirement.

The signal branch should return `128 + signal`; the normal branch continues to return `exitCode`.
