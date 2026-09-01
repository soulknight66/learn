# Sealed reference tests

`test_reference.py` is a Python 3.6-compatible black-box `unittest` suite for
the sealed implementation. It always performs a clean warning-as-error build,
then invokes `minish` as a user would; it does not link against implementation
internals.

From the repository root, run:

```sh
python3 sealed/reference_tests/test_reference.py -v
```

The cases cover token concatenation, all three quoting/escaping forms, empty
arguments, operator precedence, concurrent pipelines, last-process pipeline
status, redirection ordering and failure recovery, parent versus child builtin
effects, exit behavior, pre-execution syntax validation, stdin and `-c` modes,
background/stopped/completed job states, `fg`/`bg`, process-group creation, and
bounded cleanup at EOF. It also verifies exact job source text, status-memory
rules, arbitrary-length exit operands, external text-file fallback, missing
shebang interpreters, strict job-ID syntax, stopped-pipeline status, physical
line escape boundaries, and that a batch background reader gets
`/dev/null` while an explicit input redirection still wins. Temporary
directories isolate every filesystem test.

Two bounded regressions cover repair-specific failures: one pipeline member
resumes a stopped group before exiting, and no-argument mode starts with file
descriptor 0 closed. The expected outcomes are final-stage status 0 and quiet
EOF status 0, respectively.

Most job-state assertions use deterministic noninteractive control, avoiding
terminal echo and volatile PIDs. Four bounded pseudo-terminal cases also
verify that Ctrl-C reaches the foreground group, the prompt recovers, terminal
handoff still occurs when standard output is redirected, and an immediate
reader cannot race the handoff. They also ensure that `-c` attached to a terminal
does not emit prompt-only job notices. The input/status cases cover rejection
of embedded NUL bytes and the separate last-foreground status used by
operand-free `exit`.
