# Debugging: the command works until an argument contains spaces

A candidate controller passes `/bin/printf '%s\n' 'two words'` to its runner. The runner reports four
command operands where the caller supplied three, and a literal `*` expands to filenames.

The candidate stores all command operands in one scalar before invocation. Reproduce the failure
with a recording runner, identify every point where argv boundaries are lost, and propose a minimal
repair. Add a regression case containing whitespace, a glob, a semicolon, and an empty argument.

Do not solve this by escaping a command string or invoking another shell.
