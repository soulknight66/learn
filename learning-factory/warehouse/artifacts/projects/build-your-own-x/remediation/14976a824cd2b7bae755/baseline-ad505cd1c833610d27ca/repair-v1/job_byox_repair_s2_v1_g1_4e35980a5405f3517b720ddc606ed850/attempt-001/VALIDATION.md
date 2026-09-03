# Repair validation record

Date: 2026-09-02 (America/Chicago)

Artifact status remains **GENERATED + PARTIAL**. These are bounded builder observations from repair
generation 1, not independent validation or production certification.

The workspace login wrapper prefixed each invocation with these host identity warnings; they are not
artifact output:

```text
/usr/bin/id: cannot find name for user ID 532319
/usr/bin/id: cannot find name for group ID 500275
/usr/bin/id: cannot find name for user ID 532319
```

## Toolchain

Commands:

```bash
/usr/bin/bash --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Both exited `0`. The first version lines were:

```text
GNU bash, version 4.4.20(1)-release (x86_64-redhat-linux-gnu)
Python 3.11.5
```

The Python executable is from the configured read-only toolchain root and is invoked by its exact
absolute path below. No ShellCheck result is claimed.

## Shell syntax

Command:

```bash
/usr/bin/find starter public_tests environment sealed debugging review_exercises \
  -type f -name '*.sh' -exec /usr/bin/bash -n '{}' +
```

Observed exit `0`, with no command-produced output.

## Public contract against the repaired sealed controller

Command:

```bash
/usr/bin/env TMPDIR="$PWD/environment" /usr/bin/timeout 30s \
  /usr/bin/bash public_tests/test_contract.sh sealed/reference/tinybox.sh
```

Observed exit `0`:

```text
ok 1 - help describes the command interface
ok 2 - a traversal-shaped name gets an invalid-name rejection before path use
ok 3 - create publishes an independent rootfs copy
ok 4 - duplicate create is rejected
ok 5 - inspect emits deterministic records
ok 6 - list is sorted and machine-readable
ok 7 - run preserves argv and records the runner exit status
ok 8 - delete removes exactly an inactive container
1..8
# all 8 public checks passed
```

The second check now requires an invalid-name diagnostic; an arbitrary nonzero TODO or crash is not
accepted as evidence of validation.

## Sealed deterministic suite and completion-contention regression

Command:

```bash
/usr/bin/env TMPDIR="$PWD/environment" /usr/bin/timeout 30s \
  /usr/bin/bash sealed/reference_tests/test_reference.sh
```

Observed exit `0`. The nested public suite passed 8/8, followed by:

```text
ok 1 - sealed controller satisfies the public contract
ok 2 - operating-system root is rejected as state
ok 3 - run requires both the separator and an absolute command
ok 4 - metadata is validated as inert data
ok 5 - racing creates publish exactly one complete container
ok 6 - RUNNING state excludes run and delete until completion
ok 7 - completion survives a competing mutation holding the name lock
ok 8 - runner status 255 is preserved and recorded
ok 9 - handled TERM records EXITED rather than leaving RUNNING
1..9
# all 9 sealed checks passed
```

Check 7 starts a controlled runner, makes a real competing `delete` hold the per-name lock while
reading metadata, releases the runner while that lock remains held, and then releases the competitor.
It requires the competitor to report `RUNNING`, the primary command to return runner status `23`, and
the final record to be exactly `status=EXITED` plus `exit_code=23`. The harness bounds each marker
wait and the whole suite is bounded by 30 seconds.

## Adversarial regression suite

Command:

```bash
/usr/bin/env TMPDIR="$PWD/environment" /usr/bin/timeout 30s \
  /usr/bin/bash sealed/reference_tests/test_adversarial.sh
```

Observed exit `0`:

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

This is a finite regression suite, not fuzzing.

## Intentional starter baseline

Command:

```bash
/usr/bin/env TMPDIR="$PWD/environment" /usr/bin/timeout 30s \
  /usr/bin/bash public_tests/test_contract.sh starter/tinybox.sh
```

Observed exit `1`: help passed and checks 2 through 8 failed (`7 of 8 public checks failed`). In
particular, the incomplete starter no longer receives a false positive for the traversal-shaped
name. This nonzero result is expected for the TODO scaffold and is not recorded as a passing test.

## Host capability probe

Command:

```bash
/usr/bin/env TMPDIR="$PWD/environment" /usr/bin/timeout 30s \
  /usr/bin/bash environment/check.sh
```

Observed exit `0`:

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

This is host availability evidence only, not a security-boundary result.

## Real namespace-runner integration

Command:

```bash
/usr/bin/env TMPDIR="$PWD/environment" /usr/bin/timeout 30s \
  /usr/bin/bash sealed/reference_tests/test_real_runner.sh
```

Observed exit `0`:

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

The test creates and removes a scoped temporary rootfs. This one-host result does not establish
portability, hostile-workload containment, hardening, or production readiness.

## Final pack audit

Command:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/reference_tests/verify_pack.py
```

Observed exit `0` after the repaired content and original artifact modes were restored:

```text
PASS required regular files: 23
PASS forbidden paths absent: 21
PASS artifact entries are regular files/directories
PASS strict manifest and immutable provenance objects
PASS credential-pattern scan
```

The audit checks strict JSON without duplicate keys or nonstandard constants, exact
manifest/provenance semantics, required and forbidden paths, entry types, and common private-key and
credential token patterns. Factory marker entries and archived prior roots are not artifact material
and are outside its scan.

Command:

```bash
/usr/bin/sha256sum MANIFEST.yaml PROVENANCE.json
```

Observed exit `0`:

```text
b0005f38f7cef3f36e2bb88b22c0180da88a4acc62b575aadfd199a95e002028  MANIFEST.yaml
6c6ad5fe82b5d44f8aac9c06cb78b0b97b97a63536d8ae379dc986784f064768  PROVENANCE.json
```

## Limitations

- Independent validators remain mandatory; this builder does not publish `REVIEWED` or any other
  promotion label.
- No fuzzing, benchmark, transfer/isolation validation, cross-kernel matrix, crash recovery test,
  security certification, or production qualification was performed.
- A stale lock lasting beyond the controller's finite completion retry remains a documented recovery
  limitation; transient cooperating contention is covered by the regression.
