# Public tests

These tests expose behavior, not an implementation. Run them from the repository root:

```sh
make -C starter check
make -C starter check-milestones
make -C public_tests cli SHELL_UNDER_TEST=../starter/byosh
```

`check` is the green baseline shipped with the starter. `check-milestones` specifies the parser
features you add and is expected to fail initially. `cli` is a black-box smoke suite for a completed
shell; it accepts any executable path via `SHELL_UNDER_TEST`.

The CLI harness resolves the external utilities it needs from `PATH` and passes their absolute paths
to the shell under test; it fails clearly when one is unavailable. Each invocation starts in a fresh
session. Timeouts ask a separately bounded `ps` helper only for that session's rows, terminate
pipeline members even when they occupy distinct process groups, and reap the shell with bounded
waits. Captured stdout and stderr tails are included in timeout diagnostics. The supplied helper uses
the procps `--sid` selector and fails closed if that selector is unavailable.

The smoke suite deliberately avoids timing-sensitive job-control assertions because reliable
terminal control needs a pseudo-terminal test harness. Treat interactive testing as a separate
milestone, not as evidence supplied by these checks.
