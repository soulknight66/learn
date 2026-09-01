# Sealed reference tests

This deterministic `unittest` suite exercises the complete behavior expected
from the shell while keeping solution-bearing cases out of the learner view.
It covers literal lexing, syntax diagnostics, pipelines, redirections, status
propagation, parent-versus-child built-ins, background bookkeeping, and actual
interactive terminal job control through a pseudo-terminal. Regression cases
also close descriptors 0 and 1 across multiple pipeline positions, stress
immediate child exits while the shell is idle, and make fast foreground probes
verify terminal ownership before their first instruction. Repair regressions
also verify that an ENOEXEC file is never delegated to a host shell and that a
completed background child is reaped while a synchronized foreground fixture
remains alive.

Build the reference implementation and run all tests with:

```sh
make -C sealed/reference test
```

The tests can also validate another executable that follows the challenge
contract:

```sh
make -C sealed/reference_tests test SHELL_UNDER_TEST=/absolute/path/to/byosh
```

The suite uses only Python 3.6-compatible standard-library APIs and detected
absolute paths to ordinary POSIX user-space tools. Every tested shell runs in a
dedicated session. Timeout cleanup queries only that SID, uses bounded
TERM/KILL phases, and reaps scoped descendants when the host supports Linux
child-subreaper mode. A timeout, error, or malformed result from the scoped
process-list helper fails cleanup explicitly; the fallback revalidates and
kills only the known direct child, waits boundedly, and reports that descendant
cleanup is incomplete. Live members remaining after the bounded final sweep
also fail cleanup explicitly. Cleanup never falls back to global process
enumeration. The pseudo-terminal case is skipped when the host does not expose
`TIOCSCTTY`; all noninteractive coverage still runs.

From the repository root, the deterministic disclosure/structure audit is:

```sh
python3 sealed/reference_tests/audit_pack.py
```

It verifies the authoritative required and forbidden paths, immutable JSON
objects, regular-file boundary, local exercise-answer sealing, local Markdown
links, and a conservative set of credential/key patterns. It is a pack
integrity check, not independent functional validation.

`learner_view_allowlist.json` is the exact, versioned list of files eligible for
a learner projection. The pack audit rejects missing or extra files beneath the
three learner roots. It does not create a learner workspace and does not claim
`TRANSFER_VERIFIED`; a harness-controlled transfer must copy only the listed
regular files and independently compare the result before release.
