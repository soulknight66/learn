# Independent validation record

Date: 2026-08-31  
Verdict: **REVISE**

This is reviewer-controlled evidence from the separate review workspace. It records observed command
results but does not award `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED`, and it does not modify the candidate manifest.

Commands below were run from `CANDIDATE/` unless another directory is stated. The execution launcher
repeatedly warned that the numeric uid/gid had no name; those launcher warnings were not candidate
diagnostics and did not change command statuses.

The writable temporary directory used for successful reruns was:

```text
REVIEW_TMP=/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_review_v1_bb68cd7e2c05f8b000f3e7bfd2e54a32/attempt-001/.review-tmp.isVq8E
```

It was created with `mktemp -d` outside `CANDIDATE/` and removed after testing.

## Environment and initial reproducibility

```bash
./environment/check.sh
./environment/check.sh --require-isolation-tools
```

Both returned 0. Bash, `env`, `mktemp`, `sort`, `timeout`, `unshare`, `chroot`, `mount`, `findmnt`, and
`nsenter` were reported available. Bash was 4.4.20 on Linux 4.18.0. ShellCheck, Bats, and BusyBox were
reported missing. Independent command lookup also found no `rg` or `git`.

The default temporary directory did not exist:

```bash
test -d /tmp
# exit 1
```

Consequently, the exact default commands behaved as follows before any tests ran:

```text
timeout --kill-after=3s 90s bash sealed/reference_tests/run.sh
  exit 1 (temporary-base setup failed silently)

timeout --kill-after=3s 90s env MINICTR_BIN=sealed/reference/minictr \
  bash public_tests/test_minictr.sh
  exit 2: cd: /tmp: No such file or directory

timeout --kill-after=3s 90s bash adversarial/run.sh sealed/reference/minictr
  exit 2: cd: /tmp: No such file or directory

bash benchmarks/run.sh sealed/reference/minictr 3
  exit 1: mktemp ... /tmp/minictr-benchmark.XXXXXX: No such file or directory
```

This conflicts with the environment checker's exit-0 statement that public-test prerequisites were
found. The remaining suite runs set `TMPDIR=$REVIEW_TMP` explicitly.

## Syntax, metadata, and immutability

An independent NUL-delimited scan selected files whose first line was a Bash shebang and ran each
through `bash -n`:

```text
scripts=32 failures=0
exit=0
```

Both metadata files parsed with `python3 -m json.tool` (exit 0). File hashes were:

```text
4c518df8fff17d4ec3dab9a954ba9c6cdfe948e335d7cf4479dc60e3cfe87743  MANIFEST.yaml
1e3cf194f1724459eff9ce466c43c648953bb8fc7820b001b3e76c618d9d0ca0  PROVENANCE.json
```

The following independent semantic calculation used compact, key-sorted JSON for the embedded
`{"project": ..., "source": ...}` object:

```text
canonical_project_source_sha256=ed760f2a06241ed32edb3cc27610fe8ef57cfe8aee2ffa2aa37c2f9bf1d90ac6
manifest_provenance_sha256=ed760f2a06241ed32edb3cc27610fe8ef57cfe8aee2ffa2aa37c2f9bf1d90ac6
snapshot_sha256=ed760f2a06241ed32edb3cc27610fe8ef57cfe8aee2ffa2aa37c2f9bf1d90ac6
ids_match=True
```

This verifies internal metadata consistency, not the inaccessible source repository or all generated
artifact bytes. An aggregate of sorted per-file hashes was identical before and after all checks:

```text
66 regular files; no submitted symlinks
e93a743f4b6e1e430bf614c3c73c20fd1c43a6644e33d324461fab73d5d5a4a1  -
```

The same value before and after confirms that this review did not change `CANDIDATE/`.

## Independently executed supplied checks

```bash
TMPDIR=$REVIEW_TMP timeout --kill-after=3s 90s \
  bash sealed/reference_tests/run.sh
# exit 0: 19 passed; 0 failed

TMPDIR=$REVIEW_TMP MINICTR_BIN=sealed/reference/minictr \
  timeout --kill-after=3s 90s bash public_tests/test_minictr.sh
# exit 0: 9 passed; 0 failed

TMPDIR=$REVIEW_TMP timeout --kill-after=3s 90s \
  bash adversarial/run.sh sealed/reference/minictr
# exit 0: 34 passed; 0 failed
```

The public reference suite was repeated five times; every repetition returned 0 with `9 passed,
0 failed`.

The opt-in host probe was inspected before execution and bounded externally:

```bash
TMPDIR=$REVIEW_TMP MINICTR_RUN_REAL_TESTS=1 \
  timeout --kill-after=5s 35s bash sealed/reference_tests/real_integration.sh
# exit 0
# PASS: rootless user/mount/PID/UTS/IPC/network namespace probe
```

This is one host capability/behavior observation, not a portable isolation or security result.

The intentional starter baseline was also reproduced:

```bash
TMPDIR=$REVIEW_TMP timeout --kill-after=3s 90s bash public_tests/test_minictr.sh
# exit 1: 3 passed, 6 failed
```

The three focused debugging exercises produced the intended contrast:

```text
01-argv-boundaries: broken exit 1; sealed fixed exit 0
02-atomic-create:   broken exit 1; sealed fixed exit 0
03-exit-status:     broken exit 1; sealed fixed exit 0
```

A three-iteration runner/summarizer smoke returned 0 for all nine operations and for the summarizer:

```text
operation  samples  min_us  mean_us  max_us
create     3        59414   66323.7  77970
ps         3        35696   39433.3  42529
delete     3        33953   36157.0  37445
```

These timings merely show that the harness ran. They are not a stable performance study and do not
support a `BENCHMARKED` label.

## Targeted correctness reproductions

### Unchecked here-string failure bypasses path containment

The reviewer created a disposable rootfs below `$REVIEW_TMP` and ran:

```bash
rootfs=$REVIEW_TMP/overlap-forced/rootfs
mkdir -p "$rootfs"
TMPDIR=/definitely/nonexistent MINICTR_HOME="$rootfs/state" \
  ./sealed/reference/minictr create overlap "$rootfs"
status=$?
test -f "$rootfs/state/containers/overlap/rootfs"
```

Observed:

```text
sealed/reference/lib/runtime.sh: line 79: cannot create temp file for here-document: Permission denied
status=0
nested state record exists: yes
```

With valid temporary storage, the supplied disjoint-path test rejected the same logical overlap. The
failure is therefore a fail-open error path, not an unconditional comparison error.

### Locale-dependent names

`locale -a` included `en_US.utf8`. A direct regex probe and the CLI were run under that locale:

```bash
LC_ALL=en_US.utf8 bash -c \
  'v=é; [[ $v =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$ ]]'
# exit 0

LC_ALL=en_US.utf8 TMPDIR=$REVIEW_TMP MINICTR_HOME=$REVIEW_TMP/locale/state \
  ./sealed/reference/minictr create é "$REVIEW_TMP/locale/rootfs"
# exit 0

LC_ALL=en_US.utf8 TMPDIR=$REVIEW_TMP MINICTR_HOME=$REVIEW_TMP/locale/state \
  ./sealed/reference/minictr ps
```

Observed `é<TAB>CREATED<TAB>-<TAB>...`. Repeating `ps` with `LC_ALL=C` printed only the header, and
`delete é` returned 1 with `minictr: invalid container name: é`.

### Zombie owner classified as RUNNING

After creating a disposable `sample` registration, a Python process-control fixture forked a child,
allowed it to exit without reaping it for three seconds, and printed its PID, `/proc` start token, and
state. The exact payload was:

```bash
python3 -c 'import os,time; p=os.fork(); (os._exit(0) if p==0 else None); \
time.sleep(.1); s=open(f"/proc/{p}/stat").read(); r=s.rsplit(") ",1)[1].split(); \
print(p,r[19],r[0],flush=True); time.sleep(3); os.waitpid(p,0)'
```

While the holder retained that child, the reviewer wrote its natural two-line `PID/start-token` record
to `state/containers/sample/run` and invoked reference `ps`. Observed:

```text
fixture_state=Z
NAME    STATUS   PID  ROOTFS
sample  RUNNING  65   .../zombie-repro/rootfs
ps_status=0
```

The holder then reaped the child and exited normally.

### TERM becomes the default unshare child-death signal

The following bounded, process-only probe requested no namespace changes; it tested the semantics of
the exact `--fork --kill-child` option used by the reference:

```bash
timeout --kill-after=1s 3s bash -c '
supervisor=
cleanup() {
  if [[ -n $supervisor ]] && kill -0 "$supervisor" 2>/dev/null; then
    kill -KILL "$supervisor" 2>/dev/null || true
    wait "$supervisor" 2>/dev/null || true
  fi
}
trap cleanup EXIT TERM INT
unshare --fork --kill-child bash -c \
  "trap \"printf payload_received_TERM\\n\" TERM; printf \"payload_ready\\n\"; while :; do :; done" &
supervisor=$!
sleep 0.2
kill -TERM "$supervisor"
wait "$supervisor" 2>/dev/null
status=$?
supervisor=
printf "unshare_status=%d\n" "$status"
'
```

Observed exit 0 and:

```text
payload_ready
unshare_status=143
```

There was no `payload_received_TERM`. `unshare --help` independently stated that `--kill-child` defaults
to `SIGKILL`.

## Disclosure, license, and provenance observations

```bash
find CANDIDATE -type f -path '*/sealed/*' | wc -l
# 25

find CANDIDATE -type f \
  \( -iname 'LICENSE*' -o -iname 'COPYING*' -o -iname 'NOTICE*' \) -print
# CANDIDATE/LICENSE_BOUNDARY.md

grep -RIlE 'SPDX-License-Identifier|Copyright \(c\)|All rights reserved' CANDIDATE
# no matches
```

The sealed count includes full reference code/tests, fixed debugging scripts/answers, and model code
reviews. No machine-readable learner allowlist or projection evidence was present. A path-only scan for
common high-confidence private-key, AWS, and OpenAI-key signatures returned no matches, but this is not
a general secret-scanning guarantee.

The source catalog path recorded in `PROVENANCE.json` was not readable from the review workspace, `git`
was unavailable, and network access was restricted. The recorded source commit, CC0 evidence, upstream
license, and non-copying/authorship assertions could therefore not be compared with external source
objects. No obvious vendored dependency or Bocker-specific attribution marker was found in the
candidate-only scan; that absence does not prove independent authorship.

## Limitations

- ShellCheck, Bats, BusyBox, ripgrep, and git were unavailable.
- Source objects, upstream linked content, and the builder's immutable comparison objects were not
  available for independent comparison.
- No actual learner view or transfer harness was available; progressive-disclosure containment remains
  inconclusive outside the submitted tree.
- The real integration result applies only to this kernel, util-linux toolchain, architecture, and
  policy configuration.
- No fuzzing, hostile-rootfs escape assessment, load/soak run, transfer verification, or production
  deployment was performed.
- Supplied-script passes establish only their asserted cases. They do not by themselves justify any
  promoted validation label.
