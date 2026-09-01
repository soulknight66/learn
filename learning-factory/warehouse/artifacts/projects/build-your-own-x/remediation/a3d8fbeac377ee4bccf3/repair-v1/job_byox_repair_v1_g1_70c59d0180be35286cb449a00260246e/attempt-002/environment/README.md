# Reproducible environment

The intended native toolchain is Free Pascal 3.2.x on a POSIX-like host, plus
Python 3.6 or newer for black-box tests. The implementation uses only standard
Free Pascal units (`SysUtils` and `Classes`); no network dependencies are needed.

Run the complete public check from the repository root:

```bash
environment/check.sh
```

`FPC` can select a compiler binary and `MICA_BIN` can select an already-built
executable. The script does not install software. It exits 2 when the compiler is
unavailable and no executable was supplied, keeping an unavailable dependency
distinct from a failed build or failed test.

`check.sh` puts both the build and the complete public-suite invocation behind
explicit outer deadlines. Each candidate invocation also goes through
`harness.py`: it creates a new POSIX session, drains but quota-limits both output
streams, terminates the process group on completion or timeout, and reaps the
direct child. Source fixtures and their per-attempt directory are mode `0444` and
`0555` while the candidate runs, and the candidate receives a small deterministic
environment. This is containment for ordinary descendant processes, not a
substitute for a worker-owned container or cgroup when executing hostile native
code.

Run deterministic harness regression tests without bytecode caches:

```bash
python3 -B -m unittest environment.test_harness -v
```

`learner_view_allowlist.json` is the machine-readable transfer input. Generating
and validating an actual learner workspace remains a worker-controlled operation;
this pack does not claim `TRANSFER_VERIFIED`.

Expected build products are `starter/bin/mica` and `starter/units/*`. They are
scratch artifacts, not source or evidence by themselves.
