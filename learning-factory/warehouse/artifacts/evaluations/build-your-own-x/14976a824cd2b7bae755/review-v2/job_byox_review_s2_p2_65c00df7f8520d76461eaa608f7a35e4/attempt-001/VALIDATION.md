# Independent validation record

Date: 2026-09-02 (America/Chicago)

Scope: read-only inspection and bounded execution against CANDIDATE/. Temporary reviewer state was
created outside CANDIDATE/ and removed. The login wrapper emitted the following prefix on every
command; it is not candidate output:

~~~text
/usr/bin/id: cannot find name for user ID 532319
/usr/bin/id: cannot find name for group ID 500275
/usr/bin/id: cannot find name for user ID 532319
~~~

## Toolchain

~~~bash
python3 --version
bash --version | sed -n '1p'
command -v shellcheck
~~~

Observed:

~~~text
Python 3.6.8
GNU bash, version 4.4.20(1)-release (x86_64-redhat-linux-gnu)
# no shellcheck path; command -v returned nonzero
~~~

## Syntax and static inspection

~~~bash
find CANDIDATE/starter CANDIDATE/public_tests CANDIDATE/environment CANDIDATE/sealed \
  -type f -name '*.sh' -exec bash -n {} +
~~~

Observed exit 0; no command-produced output.

~~~bash
grep -RInE '(^|[^[:alnum:]_])(eval|source|sh -c|bash -c)([^[:alnum:]_]|$)' \
  CANDIDATE --include='*.sh'
~~~

Observed one textual match, source-rootfs. Inspection showed that it is a benign fixture path
component, not a source command; no prohibited invocation was found.

The complete 42-file submission was read. An independent filesystem inventory found zero symlinks;
all submitted shell entry points were executable mode 0555.

## Supplied deterministic suites

~~~bash
env TMPDIR="$PWD" \
  bash CANDIDATE/public_tests/test_contract.sh CANDIDATE/sealed/reference/tinybox.sh
~~~

Observed exit 0: all 8 public checks passed.

~~~bash
env TMPDIR="$PWD" bash CANDIDATE/sealed/reference_tests/test_reference.sh
~~~

Observed exit 0: the nested 8/8 public checks and all 8 sealed lifecycle, race, metadata, status,
and signal checks passed.

~~~bash
env TMPDIR="$PWD" bash CANDIDATE/sealed/reference_tests/test_adversarial.sh
~~~

Observed exit 0: all 6 symlink, invalid-name, argv-boundary, and runner-file checks passed.

~~~bash
env TMPDIR="$PWD" \
  bash CANDIDATE/public_tests/test_contract.sh CANDIDATE/starter/tinybox.sh
~~~

Observed exit 1, matching the intended scaffold baseline: checks 1-2 reported ok; checks 3-8
reported not ok.

## Public-test false positive

~~~bash
env TINYBOX_STATE_DIR="$PWD/reviewer-unused-state" \
  bash CANDIDATE/starter/tinybox.sh create ../escape \
  CANDIDATE/environment/fixtures/rootfs
~~~

Observed exit 70:

~~~text
tinybox: create is not implemented yet
~~~

No state path was created. This shows that public check 2 passes because it accepts any failure, not
because the starter actually validates the traversal-shaped name.

## Host capability and live integration

~~~bash
env TMPDIR="$PWD" timeout 30s bash CANDIDATE/environment/check.sh
~~~

Observed exit 0. All listed commands were AVAILABLE, and the probe printed:

~~~text
AVAILABLE unshare
SUPPORTED unprivileged-user-namespace
~~~

~~~bash
env TMPDIR="$PWD" timeout 30s \
  bash CANDIDATE/sealed/reference_tests/test_real_runner.sh
~~~

Observed exit 0:

~~~text
CREATE_STATUS=0
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
~~~

This is availability and functional evidence for this host only, not containment or portability
evidence.

## Independent completion-contention check

A temporary reviewer harness (removed after execution) performed this bounded schedule:

1. Create collision and start run with the supplied controlled runner.
2. Start delete collision in a Bash process where an exported mapfile wrapper sleeps for one second
   before calling the builtin. This widens the real interval in which the competing command owns the
   name lock while reading RUNNING; candidate state and code are not altered.
3. Once locks/collision.lock exists, release the first runner.
4. Wait for both controllers and inspect the container.

Executed command:

~~~bash
timeout 15s bash review_lock_race.sh
~~~

Observed harness exit 0:

~~~text
PRIMARY_STATUS=3
COMPETITOR_STATUS=3
INSPECT_STATUS=0
name=collision
status=RUNNING
exit_code=
~~~

The finishing controller lost the fail-fast lock acquisition and did not commit completion.

## Structure, manifest, and provenance

~~~bash
python3 CANDIDATE/sealed/reference_tests/verify_pack.py
~~~

Observed exit 0 with 23 required files, 21 forbidden paths absent, only regular artifact entries,
strict pinned manifest/provenance objects, and no matches from its credential-pattern scan. Because
this is builder-supplied code, its result was treated as supporting information rather than
independent proof.

Independent checks also observed:

~~~text
regular files: 42
symlinks: 0
PROVENANCE.json sha256:
  6c6ad5fe82b5d44f8aac9c06cb78b0b97b97a63536d8ae379dc986784f064768
MANIFEST.yaml sha256:
  b0005f38f7cef3f36e2bb88b22c0180da88a4acc62b575aadfd199a95e002028
~~~

The manifest identifiers agree with provenance and conservatively declare GENERATED, PARTIAL,
independent_validation: REQUIRED, and productionized: false.

## Limitations

- ShellCheck was unavailable.
- The immutable source catalog, upstream linked repository, and a materialized learner view were not
  provided; provenance derivation, no-copy similarity, upstream licensing, and sealed-view exclusion
  could not be independently verified.
- No cross-kernel matrix, fuzzing, benchmark, containment/security test, crash/power-loss test, or
  production qualification was performed or inferred.
- The completion-contention harness deliberately widens a scheduling interval; it establishes
  reachability of the faulty state, not its frequency on production storage.
