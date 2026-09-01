# Build environment

The project targets a POSIX-like host with:

- a C11 compiler (`cc`, GCC, or Clang);
- POSIX process, pipe, signal, terminal, and file-descriptor APIs;
- `make`;
- Python 3.6 or newer for the test drivers; and
- a pseudo-terminal implementation for interactive job-control tests; and
- the standard `ps` utility for session-wide timeout cleanup in stress tools.

Verified commands are recorded in `../VALIDATION.md`. Start with:

```sh
make -C starter clean all
python3 -m unittest discover -s public_tests -v
```

The code assumes Unix facilities such as `fork`, `execvp`, `pipe`, `dup2`,
`waitpid`, `setpgid`, `tcsetpgrp`, and `sigaction`; it is not expected to build
unchanged on native Windows. No third-party library or network access is
required. Sanitizer runs are optional because sanitizer availability differs by
compiler and host.

## Learner-view boundary

`VIEW_POLICY.json` is the machine-readable, exact learner allowlist. Its
default is deny: a file absent from that list is not part of a learner export,
even when it is present in the validator pack. In particular, sealed material,
exercise answers, reference tests, and validator-only tools are absent.

An authorized validator can run `python3 tools/view_integrity.py verify` at the
validator-pack root and can use its `export-learner DESTINATION` action in a
separate controlled area. The repair builder did not create a student
workspace. `ARTIFACT_INVENTORY.json` records the allowlisted view digest and a
separate validator-payload digest; the verification tool also rejects an exact
content duplicate of any sensitive file in the learner allowlist.

The standard `execvp` behavior for an executable text file with no recognized
header may invoke the platform shell for that file. This is allowed external
program behavior; `minish` itself must never send its command-line source to
`/bin/sh` for parsing.
