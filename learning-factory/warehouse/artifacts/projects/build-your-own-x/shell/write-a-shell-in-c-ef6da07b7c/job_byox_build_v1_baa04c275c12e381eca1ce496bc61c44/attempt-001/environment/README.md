# Environment

The implementation requires a POSIX-like host with:

- a C11 compiler;
- POSIX.1-2008 process, signal, pipe, wait, and terminal APIs;
- GNU Make or a compatible make implementation;
- Python 3.6 or newer for the public test runner;
- standard commands used by tests: `printf`, `true`, `false`, `tr`, `seq`, `wc`, `pwd`, `cat`, and `sleep`.

No network access or third-party package installation is required. Run the non-mutating probe from the repository root:

```sh
sh environment/probe.sh
```

Interactive job-control behavior needs a controlling terminal and cannot be inferred from redirected batch tests alone. Sanitizers are helpful but optional and may not be installed on every validator.
