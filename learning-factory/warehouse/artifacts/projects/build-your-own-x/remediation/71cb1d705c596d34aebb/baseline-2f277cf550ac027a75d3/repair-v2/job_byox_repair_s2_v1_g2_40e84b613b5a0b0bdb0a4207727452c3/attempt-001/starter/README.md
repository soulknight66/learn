# Starter scaffold

The scaffold handles invocation, input framing, and diagnostic plumbing. Its
`execute_line` function is deliberately incomplete and returns status 2 for a
nonblank command. Replace the TODO with your parser and execution engine; you
may split it into as many modules as useful.

Build with `make`. The target honors `CC`, `CPPFLAGS`, `CFLAGS`, and `LDFLAGS`.
`make check` runs the public black-box suite against `starter/msh` with the
configured Python 3.11.5 path. The suite requires Python 3.9 or newer; set
`PYTHON=/path/to/python3` to use another compatible interpreter.
