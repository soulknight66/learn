# Independent validation record

Review date: 2026-08-31. Verdict: **REVISE**.

`CANDIDATE/` was inspected read-only. Its files were mode 0444, so builds ran in
a writable staging copy, `.review-scratch`, made from the candidate. The copy
and review temp directory were removed after validation. The command wrapper
printed harmless numeric user/group lookup warnings before many commands; they
are omitted from excerpts below.

In command excerpts, `REVIEW_TMP` denotes the absolute path to the writable
workspace-local `.review-tmp` directory used during the run.

## Environment and inventory

Observed tools:

```text
Python 3.6.8
gcc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
GNU Make 4.2.1
```

`rg` and `git` were unavailable, so bounded `find`, `grep`, and direct file
inspection were used. The candidate contained 68 regular files (6,507 lines,
about 500 KiB), no symlinks, and no special files. This aggregate fingerprint
was taken before testing:

```sh
find CANDIDATE -type f -print0 | sort -z | \
  xargs -0 sha256sum | sha256sum
```

Observed:

```text
ab2c4fe0114a470869ef970bd20b8f0e13f539009ff10f85f10b980c375f50f5  -
```

A file-mode/build-product inspection found every candidate file at mode 0444
and found no `*.o`, `*.a`, `minish`, `*.pyc`, core file, symlink, or special
file. A credential-pattern scan had one lexical false positive at the ordinary
C declaration `Token *token = ...`; manual inspection found no credible secret.

## Metadata

Both JSON-bearing files were parsed with duplicate-key rejection. Cross-record
assertions checked project ID, source ID, source commit, snapshot reference,
status, labels, independent-validation requirement, and production flag:

```sh
python3 -c 'import json; m=json.load(open("CANDIDATE/MANIFEST.yaml")); p=json.load(open("CANDIDATE/PROVENANCE.json")); assert m["project_id"]==p["project"]["project_id"]; assert m["source_id"]==p["source"]["source_id"]==p["project"]["source_id"]; assert m["source_commit"]==p["source"]["commit_hash"]==p["project"]["metadata"]["provenance"]["source_commit"]; assert m["provenance_sha256"]==p["snapshot_sha256"]; assert m["status"]=="GENERATED" and m["validation_labels"]==["GENERATED","PARTIAL"] and m["independent_validation"]=="REQUIRED" and m["productionized"] is False; print("identity/status assertions: OK")'
```

Observed exit 0 and `identity/status assertions: OK`. File hashes were:

```text
7f48fa599d87e1a92a8e1a2cb7b8818848024a2188ef6602ec06aa64369779c9  MANIFEST.yaml
1af66d8f2f62445463a14c74c203620c23213bed4cb5e31eaada2408e3e4c1f1  PROVENANCE.json
```

The manifest's `provenance_sha256` is instead the internally declared source
snapshot value `9a2f...bf92b`; no schema was supplied to establish broader
semantics. The linked tutorial/source snapshot was unavailable, so provenance
authenticity and no-copy claims remain inconclusive.

## Public starter checks

The documented command initially could not create a Python temporary directory
in this restricted reviewer sandbox:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s public_tests -v
```

Observed exit 1, `Ran 0 tests`, and `FileNotFoundError: No usable temporary
directory found in ['/tmp', '/var/tmp', '/usr/tmp', ...]`. This was an
environment limitation, not a test failure. With a workspace-local temporary
directory:

```sh
timeout --signal=TERM --kill-after=5s 45s \
  env TMPDIR="$REVIEW_TMP" PYTHONDONTWRITEBYTECODE=1 LC_ALL=C \
  python3 -m unittest discover -s public_tests -v
```

Observed exit 0:

```text
Ran 9 tests in 0.493s
OK
```

The suite is not durable after learner progress. Its physical-line case requires
status 2 and `tokenization is a TODO` for `not-implemented`, whereas the public
requirements require status 127 for a missing command. Running the completed
reference over identical bytes demonstrates the conflict:

```sh
timeout --signal=TERM --kill-after=1s 3s \
  sealed/reference/minish -c $'   \nnot-implemented'
```

Observed exit 127 and:

```text
minish: not-implemented: No such file or directory
```

## Candidate-authored reference suite

```sh
timeout --signal=TERM --kill-after=5s 75s \
  env TMPDIR="$REVIEW_TMP" PYTHONDONTWRITEBYTECODE=1 LC_ALL=C \
  python3 sealed/reference_tests/test_reference.py -v
```

Observed exit 0:

```text
Ran 51 tests in 2.378s
OK
```

The suite performed its own clean strict build and passed all listed batch,
process, job, and four PTY cases. This is useful reproducibility evidence, but
because the implementation and suite share the same builder, it does not alone
prove `TESTED` or correctness.

Two consecutive clean builds in the same staging path produced the same hash:

```sh
sha256sum sealed/reference/minish
make -C sealed/reference clean all
sha256sum sealed/reference/minish
```

Both observations were:

```text
3ced0c93821042507a8fb62c56f651e37b2fbcb99a684f1f8537989aa561fba1  sealed/reference/minish
```

## Independent behavioral checks

The following bounded regression exposed stale foreground job state:

```sh
timeout --signal=TERM --kill-after=1s 4s sealed/reference/minish -c \
  "sh -c 'kill -STOP \$\$; sleep 0.30' | sh -c 'sleep 0.05; kill -CONT 0; sleep 0.10'"
```

Observed exit 147 and no output. The second pipeline member resumes the stopped
group before it exits. The first member is therefore running, and a conforming
shell should wait for it and ultimately return the rightmost member's status 0.
Source inspection found the foreground call uses only
`waitpid(-job->pgid, ..., WUNTRACED)`; it never requests continued events.

Closed stdin also exposed nontermination:

```sh
timeout --signal=TERM --kill-after=1s 1s sealed/reference/minish <&-
```

Observed exit 124 with no output. Source inspection showed that the internal
self-pipe can reuse fd 0 and is then polled as both stdin and notification input.

A separate bounded edge matrix observed the following expected results:

```text
literal $, #, *, ?, [, ], ~, (, ) arguments: status 0, all preserved literally
vertical-tab/form-feed/carriage-return separators: status 0, three words
external SIGTERM: status 143
redirection-only command: status 2, no file created
invalid && after an output redirection: status 2, target file absent
arbitrarily long negative exit operand ending in 1: status 255
failed redirection on exit followed by printf: status 0, printed alive
fg and bg in pipeline child context: diagnostic emitted; final cat status 0
SIGHUP-ignoring background child at shell end: bounded shutdown, status 0
```

These checks used argv-based invocations of the staged reference under 3–4
second outer deadlines. They supplement rather than duplicate the builder suite.

## Adversarial, benchmark, and exercises

```sh
timeout --signal=TERM --kill-after=5s 80s \
  env TMPDIR="$REVIEW_TMP" PYTHONDONTWRITEBYTECODE=1 LC_ALL=C \
  python3 adversarial/run.py --timeout 5 --max-output 800 \
  sealed/reference/minish
```

Observed exit 0. All ten cases were labelled `completed(status=0)`; notable
outputs included 1,048,576 bytes counted through the large pipeline, recovery
after one syntax error, and 7 bytes through the 16-stage pipeline. The runner
has no oracle, so this does not prove correctness or `FUZZED`.

```sh
python3 benchmarks/run.py --iterations 1 --warmup 0 --timeout 5 \
  sealed/reference/minish
```

Observed exit 0 for all six workloads. Single-sample medians ranged from 2.341
ms to 4.366 ms. This was only a harness smoke and does not support
`BENCHMARKED`.

All eight exercise sources passed:

```sh
gcc -std=c11 -Wall -Wextra -Wpedantic -Werror -fsyntax-only PATH
```

Bounded compiled runs then observed:

```text
eof_hang/buggy: status 124 after printing "message reached consumer"
eof_hang/fixed: status 0 with the same payload
pipeline_launcher/buggy: status 124
wait_race/buggy: status 0, reported foreground result 7 from background PID
wait_race/fixed: status 0, reported foreground result 42 from foreground PID
token_vector/fixed with six words: status 0, printed all six indexed words
```

These results support the exercises' learner-facing diagnoses.

## Unavailable checks

The builder's documented ASan failure reproduced:

```text
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
collect2: error: ld returned 1 exit status
```

An independent UBSan build also failed to link because
`/usr/lib64/libubsan.so.1.0.0` is absent. Valgrind, Clang, a fuzzer, upstream
source access, cross-platform runners, syscall fault injection, and a
machine-readable learner-view export were unavailable. No claims are inferred
for sanitizer cleanliness, leak freedom, fuzzing, transfer, review,
benchmarking, productionization, or upstream provenance.

## Immutability check

After all staged runs, the read-only `CANDIDATE/` aggregate SHA-256 was recomputed
with the inventory command above and remained
`ab2c4fe0114a470869ef970bd20b8f0e13f539009ff10f85f10b980c375f50f5`.
