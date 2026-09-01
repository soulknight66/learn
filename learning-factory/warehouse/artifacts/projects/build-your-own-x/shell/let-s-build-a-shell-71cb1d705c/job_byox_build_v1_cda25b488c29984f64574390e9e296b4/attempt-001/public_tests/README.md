# Public tests

These tests check only the starter contract: a warning-clean build, the public
C interfaces, command-line help, physical-line splitting for `-c`, empty input,
clean noninteractive EOF, and usage/NUL-input errors. They intentionally do not
contain tokenization, parsing, process, pipe, redirection, or job-control
answers.

From the repository root, run:

```sh
python3 -m unittest discover -s public_tests -v
```

The tests copy `starter/` to a temporary directory before building, so they do
not leave compiler output in the learner's tree. These are baseline checks, not
a complete specification or a substitute for independent validation.
