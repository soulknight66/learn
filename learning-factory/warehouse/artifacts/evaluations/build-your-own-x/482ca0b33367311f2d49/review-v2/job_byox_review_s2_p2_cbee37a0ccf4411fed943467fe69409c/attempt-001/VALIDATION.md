# Independent validation evidence

Review date: 2026-09-02 (America/Chicago). Commands ran from the review workspace root unless a
different directory is stated. `CANDIDATE/` was inspected and executed read-only; scratch data lived
under `.review-tmp/` and was removed after validation.

The task-specific root used in the command transcripts was:

```bash
REVIEW_ROOT=/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_review_s2_p2_cbee37a0ccf4411fed943467fe69409c/attempt-001
cd "$REVIEW_ROOT"
mkdir -p "$REVIEW_ROOT/.review-tmp"
```

The command wrapper printed these unrelated identity warnings before shell commands:

```text
/usr/bin/id: cannot find name for user ID 532319
/usr/bin/id: cannot find name for group ID 500275
/usr/bin/id: cannot find name for user ID 532319
```

They did not alter the recorded child exit codes.

## Toolchains

Commands:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
```

Both exited `0`. Observed output:

```text
Python 3.11.5
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
```

The JDK is configured but not useful to this Python-only artifact, so no Java build was attempted.

## Candidate integrity and syntax

Commands:

```bash
(cd CANDIDATE && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum)
find CANDIDATE -mindepth 1 ! -type f ! -type d -print
find CANDIDATE -type f | wc -l
find CANDIDATE -type d | wc -l
/usr/bin/timeout 30s env PYTHONPYCACHEPREFIX="$PWD/.review-tmp/pycache" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m compileall -q -f \
  CANDIDATE/starter CANDIDATE/public_tests CANDIDATE/sealed/reference \
  CANDIDATE/sealed/reference_tests
```

Observed results:

- The sorted relative-path/per-file hash inventory aggregated to
  `0bcf7f690a648a5c49efe5f6f623e35b258b00a8eb567bbec9aab1db9512bf7b` before and after review.
- The special-entry search exited `0` with no paths.
- Counts were 56 regular files and 19 directories.
- `compileall` exited `0` with no diagnostics; bytecode went only to scratch.

## Builder-suite reproduction

The default system temp locations are unavailable in this sandbox. The first unadjusted test attempt
therefore failed before exercising most code with `FileNotFoundError: No usable temporary directory`;
that environmental result was not attributed to the submission. A dedicated writable parent scratch
directory was then supplied:

```bash
cd "$REVIEW_ROOT/CANDIDATE"
/usr/bin/timeout 30s env \
  TMPDIR="$REVIEW_ROOT/.review-tmp" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v
```

Observed exit `0`:

```text
Ran 11 tests in 0.485s
OK
```

The same setup against the intentional starter exited `1`:

```bash
cd "$REVIEW_ROOT/CANDIDATE"
/usr/bin/timeout 30s env \
  TMPDIR="$REVIEW_ROOT/.review-tmp" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=starter \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v
```

```text
Ran 11 tests in 0.064s
FAILED (errors=17)
```

All 17 errors were numbered starter `NotImplementedError` sites, as intended.

The sealed suite in immutable `CANDIDATE/` used the parent `TMPDIR`, but its CLI test deliberately
replaced the subprocess environment and omitted that variable:

```bash
cd "$REVIEW_ROOT/CANDIDATE"
/usr/bin/timeout 30s env \
  TMPDIR="$REVIEW_ROOT/.review-tmp" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/reference_tests -v
```

Observed exit `1`:

```text
Ran 25 tests in 1.783s
FAILED (failures=1)
AssertionError: 125 != 0
```

The other 24 cases passed. Inspection showed the CLI-created container recorded exit 125 because
`ProcessRunner` could not create its default `TemporaryFile` with no writable system temp or cwd.

To separate that environmental assumption from code/test behavior, the candidate was copied to
scratch, its content inventory was confirmed identical, and only scratch permissions were made
writable:

```bash
cd "$REVIEW_ROOT"
cp -a CANDIDATE .review-tmp/CANDIDATE-copy
chmod -R u+w .review-tmp/CANDIDATE-copy
(cd .review-tmp/CANDIDATE-copy && \
  find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum)
cd .review-tmp/CANDIDATE-copy
/usr/bin/timeout 30s env \
  TMPDIR="$REVIEW_ROOT/.review-tmp" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/reference_tests -v
```

The copied inventory had the same aggregate `0bcf7f…bf7b`. The suite exited `0`:

```text
Ran 25 tests in 3.625s
OK
```

This corroborates the builder's local 25-test observation but also demonstrates an undocumented
writable-temp/cwd dependency.

## Independent contract probes

A reviewer-created `unittest` script (scratch SHA-256
`193e8c87b75a8cbda6f204915fb67b906bc50f32f3802887af0c6f5d6c2b1d2e`) exercised six cases against
the unmodified sealed reference. Each case used `TemporaryDirectory`; the concurrency case used two
threads, a two-party barrier with a three-second timeout, and different valid tars.

Command:

```bash
cd "$REVIEW_ROOT"
/usr/bin/timeout 30s env \
  TMPDIR="$REVIEW_ROOT/.review-tmp" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=CANDIDATE/sealed/reference:CANDIDATE \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  .review-tmp/review_probes.py
```

Observed exit `1`, `Ran 6 tests in 0.422s`, `FAILED (failures=6)`:

1. `test_layer_rejects_a_destination_below_a_symlink_parent`: expected `InvalidLayer` or
   `PathEscape`, but no exception was raised and the outside payload existed.
2. `test_layer_preflight_does_not_partially_apply_before_type_error`: `InvalidLayer` was raised for an
   opaque marker below an existing file, but an earlier whiteout had already deleted `victim`.
3. `test_truncation_marker_stays_inside_the_byte_bound`: a five-byte limit produced 21 UTF-8 bytes.
4. `test_published_image_content_cannot_be_changed_through_returned_path`: changing `original` to
   `tampered` through `ImageRecord.rootfs` caused the next container snapshot to contain `tampered`.
5. `test_layer_bytes_used_for_hash_and_application_are_the_same`: after a controlled change between
   hashing and application, the recorded digest remained for the original tar while rootfs held
   `applied` rather than `hashed`.
6. `test_failed_racing_import_does_not_leave_its_published_object`: outcomes were one success and one
   conflict, while two image directories remained instead of one.

These are focused counterexamples, not fuzzing or a general security audit.

## Manifest, provenance, and static audits

Commands:

```bash
cd "$REVIEW_ROOT"
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'import json; m=json.load(open("CANDIDATE/MANIFEST.yaml")); p=json.load(open("CANDIDATE/PROVENANCE.json")); assert (m["project_id"],m["source_id"],m["source_commit"],m["provenance_sha256"]) == (p["project"]["project_id"],p["source"]["source_id"],p["source"]["commit_hash"],p["snapshot_sha256"]); print("identity_match=true")'
sha256sum CANDIDATE/MANIFEST.yaml CANDIDATE/PROVENANCE.json
grep -RInE --include='*.py' \
  '\.extract(all)?\(|shell[[:space:]]*=[[:space:]]*True' \
  CANDIDATE/starter CANDIDATE/sealed/reference
grep -RInE --include='*.md' --include='*.py' --include='*.json' --include='*.yaml' \
  'AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|(password|passwd|api[_-]?key|access[_-]?token)[[:space:]]*[:=][[:space:]]*[^[:space:]]+' \
  CANDIDATE
```

Observed:

- Identity assertion exited `0` and printed `identity_match=true`.
- Byte hashes were `4eb8b23f9c116db38a01876763e2e4f97e22c4219c9446bf949bb7e374c43123`
  for `MANIFEST.yaml` and `266aadf01d684512a09ebed6ddd12fdbb424c6b2c27bb676147ce4df18d37705`
  for `PROVENANCE.json`.
- Both textual scans produced no matches. The credential command's no-match status was interpreted as
  success; it is only a pattern scan.
- Manifest values were `status: GENERATED`, labels `GENERATED` and `PARTIAL`,
  `productionized: false`, and `independent_validation: REQUIRED`.

## Limitations

- Network and the named immutable source baseline were unavailable, so upstream provenance, license
  evidence, and the no-copy assertion remain unverified.
- No benchmark, fuzz campaign, profiler, transfer test, production deployment, hostile workload,
  elevated execution, or kernel-isolation test was performed.
- Text scans cannot exclude every secret encoding or dynamic forbidden call.
- A PASS verdict would still be advisory; this review assigns `REVISE` and does not publish a
  `REVIEWED` label.
