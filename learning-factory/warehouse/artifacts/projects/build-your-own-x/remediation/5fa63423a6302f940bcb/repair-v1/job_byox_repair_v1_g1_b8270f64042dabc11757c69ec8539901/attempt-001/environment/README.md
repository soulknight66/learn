# Development Environment

This project targets a POSIX-like Unix environment with process groups, a controlling terminal, and the
usual C process APIs. A plain C compiler is enough for early milestones; interactive job-control tests
also require pseudo-terminal support.

## Required tools

- a C compiler with C11 support;
- POSIX development headers and the platform C library;
- `make`;
- standard command-line utilities used by the public test fixtures;
- Python 3 when running the supplied test harness.

The normal learner workflow is:

```sh
sh environment/check_toolchain.sh
cd starter
make clean
make
```

Run `check_toolchain.sh` from the repository root; it reports whether the three command-line tools are
available without installing or changing anything. Run test commands from the locations specified by
the repository READMEs so relative fixture paths are predictable. The program itself must not assume
the repository's absolute path, username, terminal size, or current working directory.

## Useful optional tools

A debugger, system-call tracer, memory checker, and compiler sanitizers can shorten diagnosis, but they
are optional and may not be installed. Detect them before use and keep ordinary builds and tests
independent of them.

Typical diagnostic categories are:

- address and undefined-behavior checks for memory and type errors;
- file-descriptor inspection for leaked pipe ends;
- process inspection for groups, states, and zombies;
- system-call tracing for failed opens, descriptor duplication, execution, waits, and signals;
- a pseudo-terminal driver for interactive transcripts.

Use the syntax documented by the tools available on your host. Instrumented timing and signal behavior
can differ from an ordinary run, so always reproduce a fix with the normal build too.

## Reproducible test isolation

- Create a new temporary directory for each filesystem test and remove it afterward.
- Supply a controlled environment, especially `PATH` and `HOME`, when behavior depends on them.
- Use fixture programs rather than host-specific commands when exact output or exit status matters.
- Give every subprocess interaction a timeout and preserve captured standard output, standard error,
  and exit status on failure.
- For interactive tests, allocate a pseudo-terminal and clean up its complete process group.
- Do not run the shell with elevated privileges or use important files as redirection targets.

Containers can isolate files and dependencies, but job control additionally depends on how the
container is given a terminal. A test passing with piped input does not establish that foreground
terminal ownership works.

## Portability boundary

The required behavior assumes POSIX process, descriptor, signal, process-group, and terminal semantics.
Native environments without those interfaces need a compatibility layer and are not direct targets.
Compiler-specific extensions should not be necessary. When a platform exposes a behavioral difference,
document it and keep platform conditionals narrow rather than weakening the common contract.
