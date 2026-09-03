# Public tests

`run.sh IMPLEMENTATION_DIR` builds the selected implementation, compiles `test_core.c` against its lexer and parser, and runs a small end-to-end suite against its `minish` executable.

Examples:

```sh
public_tests/run.sh starter
CC=/path/to/gcc PYTHON=/path/to/python3 public_tests/run.sh my-implementation
```

These tests sample quoting, adjacent operators, comments, syntax rejection, a pipeline, exit status, and output redirection. They do not exhaust failure cleanup, process-group races, terminal handoff, descriptor leaks, or adversarial input. Do not infer unspecified behavior from test implementation details; `REQUIREMENTS.md` is authoritative.
