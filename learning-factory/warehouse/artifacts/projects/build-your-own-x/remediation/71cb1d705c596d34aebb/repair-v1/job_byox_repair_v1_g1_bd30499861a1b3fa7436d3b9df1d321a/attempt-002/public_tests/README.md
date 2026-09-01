# Public tests

The default suite is a permanent contract for both the pristine scaffold and a
completed shell. It checks a warning-clean build, public C interfaces, command-
line help, empty physical lines, clean noninteractive EOF, and usage/NUL-input
errors. It never requires a `TODO` message or another implementation detail.

From the repository root, run:

```sh
python3 -m unittest discover -s public_tests -v
```

The tests copy `starter/` to a temporary directory before building, so they do
not leave compiler output in the learner's tree.

`scaffold_smoke.py` is a one-time check for an unchanged checkout. It confirms
that the initial lexer placeholder is reachable, and is intentionally excluded
from unittest discovery. Stop running it as soon as implementation begins.

After completing a stage, run its cumulative observable check:

```sh
python3 public_tests/run_milestone.py lexer
python3 public_tests/run_milestone.py parser
python3 public_tests/run_milestone.py process
python3 public_tests/run_milestone.py descriptor
python3 public_tests/run_milestone.py job
python3 public_tests/run_milestone.py terminal
```

`all` runs every milestone. The lexer and parser stages use public API probes;
later stages use the executable, and the terminal stage uses a real pseudo-
terminal. A stage test is expected to fail until that stage is implemented.
These examples remain smaller than the full specification and never replace
independent validation.
