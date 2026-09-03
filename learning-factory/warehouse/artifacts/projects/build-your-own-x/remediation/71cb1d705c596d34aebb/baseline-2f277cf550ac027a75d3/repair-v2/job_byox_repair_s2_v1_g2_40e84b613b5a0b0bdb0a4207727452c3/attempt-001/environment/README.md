# Reproducible environment notes

The project requires a POSIX-like host with `fork`, `execvp`, `pipe`,
`setpgid`, `waitpid`, and terminal-control APIs. No third-party C libraries are
required.

The generation host exposes these pinned tools:

- C compiler: `/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc`
- Python runner: `/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3`

The test harness requires Python 3.9 or newer. The starter Makefile's `PYTHON`
variable defaults to that pinned 3.11.5 executable and may be overridden with
another compatible absolute path. Invoke the pinned paths when reproducing
`VALIDATION.md`. `/bin/sh`, `printf`,
`grep`, `tr`, and `cat` are runtime fixtures for black-box tests; their output
is used only for shell behavior, not as build dependencies. Job-control tests
also require a controlling pseudo-terminal.

`audit.py` distinguishes the authoritative source-snapshot identifier in the
manifest from the SHA-256 of the provenance document. It verifies both the
immutable manifest object and the pinned byte digest of `PROVENANCE.json`.
