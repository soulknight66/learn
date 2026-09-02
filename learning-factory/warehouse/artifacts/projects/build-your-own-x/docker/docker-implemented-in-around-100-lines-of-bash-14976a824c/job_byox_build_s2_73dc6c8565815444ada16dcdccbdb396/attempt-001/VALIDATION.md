# Validation record

Date: 2026-09-02 (America/Chicago)

Artifact status remains **GENERATED + PARTIAL**. These are generator-run observations, not
independent validation and not production certification.

The workspace login wrapper prefixed every shell invocation with these host identity warnings; they
are not output from the artifact commands:

```text
/usr/bin/id: cannot find name for user ID 532319
/usr/bin/id: cannot find name for group ID 500275
/usr/bin/id: cannot find name for user ID 532319
```

## Shell syntax

Command:

```bash
find starter public_tests environment sealed -type f -name '*.sh' -exec bash -n {} +
```

Observed: exit `0`, with no command-produced output.

`shellcheck` was queried with `command -v shellcheck`; it returned no path. No ShellCheck result is
claimed. The available interpreter reported `Python 3.6.8`.

## Public contract against the sealed controller

Command:

```bash
bash public_tests/test_contract.sh sealed/reference/tinybox.sh
```

Observed exit: `0`.

```text
ok 1 - help describes the command interface
ok 2 - a traversal-shaped name is rejected before path use
ok 3 - create publishes an independent rootfs copy
ok 4 - duplicate create is rejected
ok 5 - inspect emits deterministic records
ok 6 - list is sorted and machine-readable
ok 7 - run preserves argv and records the runner exit status
ok 8 - delete removes exactly an inactive container
1..8
# all 8 public checks passed
```

## Sealed deterministic tests

Command:

```bash
bash sealed/reference_tests/test_reference.sh
```

Observed exit: `0`. The command first repeats the eight public checks above, then reports:

```text
ok 1 - sealed controller satisfies the public contract
ok 2 - operating-system root is rejected as state
ok 3 - run requires both the separator and an absolute command
ok 4 - metadata is validated as inert data
ok 5 - racing creates publish exactly one complete container
ok 6 - RUNNING state excludes run and delete until completion
ok 7 - runner status 255 is preserved and recorded
ok 8 - handled TERM records EXITED rather than leaving RUNNING
1..8
# all 8 sealed checks passed
```

## Adversarial regression tests

Command:

```bash
bash sealed/reference_tests/test_adversarial.sh
```

Observed exit: `0`.

```text
ok 1 - a symlinked state-layout directory is rejected
ok 2 - a symlinked container cannot redirect deletion
ok 3 - symlinked metadata is rejected
ok 4 - invalid name classes are rejected without publication
ok 5 - spaces and shell syntax remain inert argv data
ok 6 - a symlink is not accepted as the configured runner file
1..6
# all 6 adversarial checks passed
```

This was a finite regression suite, not fuzzing.

## Intentional starter baseline

Command:

```bash
bash public_tests/test_contract.sh starter/tinybox.sh
```

Observed exit: `1`, as expected for the TODO scaffold.

```text
ok 1 - help describes the command interface
ok 2 - a traversal-shaped name is rejected before path use
not ok 3 - create publishes an independent rootfs copy
not ok 4 - duplicate create is rejected
not ok 5 - inspect emits deterministic records
not ok 6 - list is sorted and machine-readable
not ok 7 - run preserves argv and records the runner exit status
not ok 8 - delete removes exactly an inactive container
1..8
# 6 of 8 public checks failed
```

## Host capability probe

Command:

```bash
bash environment/check.sh
```

Observed exit: `0`.

```text
AVAILABLE bash
AVAILABLE chroot
AVAILABLE cp
AVAILABLE hostname
AVAILABLE mkdir
AVAILABLE mktemp
AVAILABLE mount
AVAILABLE mv
AVAILABLE rm
AVAILABLE sort
AVAILABLE unshare
SUPPORTED unprivileged-user-namespace
```

This probe establishes availability only. It does not establish a security boundary.

## Real namespace-runner integration

The first reproducible live attempt used util-linux `unshare 2.32.1` and exposed an unsupported newer
option in the initial runner. Command:

```bash
bash sealed/reference_tests/test_real_runner.sh
```

Observed exit: `77`.

```text
live
unshare: unrecognized option '--root=/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_build_s2_73dc6c8565815444ada16dcdccbdb396/attempt-001/tinybox-real-runner.6yGB7N/state/containers/live/rootfs'
Try 'unshare --help' for more information.
CREATE_STATUS=0
RUN_STATUS=1
INSPECT_STATUS=0
name=live
status=EXITED
exit_code=1
BLOCKED real namespace runner did not complete the probe
```

The reference runner was changed to use the available host `chroot` for its final root switch while
continuing to pass the command as argv. The test was expanded to inspect the UTS hostname and the PID
view. Final command:

```bash
bash sealed/reference_tests/test_real_runner.sh
```

Final observed exit: `0`.

```text
CREATE_OUTPUT=live
CREATE_STATUS=0
TRUE_OUTPUT=
TRUE_STATUS=0
HOSTNAME_OUTPUT=live
HOSTNAME_STATUS=0
PS_OUTPUT=      1 ps
PS_STATUS=0
INSPECT_STATUS=0
name=live
status=EXITED
exit_code=0
PASS real namespace runner completed the probe
```

The probe rootfs was built from the host's `true`, `hostname`, and `ps` executables plus dependencies
reported by `ldd`, inside a scoped temporary directory removed by the test. This single-host probe is
not portability, hardening, transfer, or production evidence.

## Informative harness failure retained

The first public-suite attempt assumed `/tmp` existed. Command:

```bash
bash public_tests/test_contract.sh sealed/reference/tinybox.sh
```

Observed exit: `1` before any contract check:

```text
mktemp: failed to create directory via template ‘/tmp/tinybox-public.XXXXXX’: No such file or directory
```

All harnesses now use a writable `TMPDIR` when supplied and otherwise a temporary directory beneath
the current working directory. The successful results above are from the corrected harness.

## Final artifact audit

Command:

```bash
python3 sealed/reference_tests/verify_pack.py
```

Observed exit: `0`.

```text
PASS required regular files: 23
PASS forbidden paths absent: 21
PASS artifact entries are regular files/directories
PASS strict manifest and immutable provenance objects
PASS credential-pattern scan
```

The audit ignores factory-owned workspace marker entries and examines the generated material paths.
It rejects duplicate/non-standard JSON, pins semantic JSON content, checks every authoritative path,
checks every forbidden path, rejects symlinks/special artifact entries, and scans text for common
private-key and credential token formats. Independent validators remain mandatory.
