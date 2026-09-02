# Independent validation record

Date: 2026-09-02 (America/Chicago). Commands ran in the supplied review workspace, with suite commands
run from `CANDIDATE/`. Temporary files and bytecode were redirected to `.review-tmp/` outside the
immutable candidate. The command wrapper repeatedly emitted numeric UID/GID lookup warnings; they did
not replace child exit codes and are omitted below.

## Toolchains

```bash
/usr/bin/timeout 10s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/timeout 10s /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
```

Both exited 0. Observed:

```text
Python 3.11.5
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
```

Java was available but was not useful for this standard-library Python pack.

## Integrity, syntax, and structure

```bash
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
find CANDIDATE -mindepth 1 ! -type f ! -type d -print
find CANDIDATE -type f | wc -l
/usr/bin/timeout 30s env PYTHONPYCACHEPREFIX="$PWD/.review-tmp/compile" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m compileall -q -f CANDIDATE
```

The inventory digest was
`f65a641e38836de14a21804480007011b920123b7137c8fe36055f82df17c06b` both before and after
execution. The special-entry search printed nothing, the file count was 60, and compilation exited 0
without diagnostics. No `__pycache__`, `.pyc`, or validation scratch appeared inside the candidate.

## Supplied suites

```bash
/usr/bin/timeout 30s env TMPDIR=../.review-tmp/public PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v

/usr/bin/timeout 45s env TMPDIR=../.review-tmp/sealed PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/reference_tests -v

/usr/bin/timeout 30s env TMPDIR=../.review-tmp/starter PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=starter \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v
```

Observed summaries:

```text
Reference/public: Ran 11 tests in 0.722s — OK (exit 0)
Sealed evaluator: Ran 37 tests in 4.603s — OK (exit 0)
Untouched starter: Ran 11 tests in 0.079s — FAILED (errors=17, exit 1)
```

Every starter error was an explicit numbered `NotImplementedError`, the expected evidence that the
learner scaffold was not pre-solved. Supplied tests were treated as corroboration, not as proof by
themselves.

## Learner-view boundary

```bash
/usr/bin/timeout 10s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/export_student_view.py --source . --check

/usr/bin/timeout 15s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/export_student_view.py --source . \
  --destination /projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g2_a90920a4741b31ba7cca01f43050f186/attempt-001/.review-tmp/student-view
```

Both exited 0 and reported `{"files":28,"status":"ok"}`. A separate hash/mode/path comparison of
the export against `environment/student_view_allowlist.json` exited 0 with:

```text
files=28 exact_allowlist=true regular_0644=true byte_identical=true
```

No evaluator root was present. The exported `environment/COPYING_NOTICE.md` contained the operative
grant, preservation instruction, `CC0-1.0` catalog boundary, and linked-resource `NOASSERTION` term.

## Static and record audits

```bash
grep -RInE --include='*.py' '\.extract(all)?\(|shell[[:space:]]*=[[:space:]]*True' \
  starter sealed/reference environment public_tests sealed/reference_tests || true
grep -RInF --include='*.py' 'execute(f' starter sealed/reference environment || true
grep -RInF --include='*.py' 'os.system(' starter sealed/reference environment || true
```

These searches printed no matches. An AST import audit parsed 21 implementation/export Python files
and reported `non_stdlib_imports []`. A bounded obvious-secret scan printed no match; these textual
checks cannot exclude dynamic calls or encoded credentials.

The independent identity check observed:

```text
manifest_sha256=4eb8b23f9c116db38a01876763e2e4f97e22c4219c9446bf949bb7e374c43123
provenance_byte_sha256=266aadf01d684512a09ebed6ddd12fdbb424c6b2c27bb676147ce4df18d37705
identity_fields_match=true status=GENERATED labels=GENERATED,PARTIAL
```

The manifest's `provenance_sha256` is the declared snapshot identifier, not the provenance file's byte
hash, matching the explicit distinction in `LICENSE_BOUNDARY.md`.

## Reviewer-authored functional probes

An ephemeral reviewer harness was stored only in external scratch, with SHA-256
`8f4bdca1f7183da7c3aef5eaf078c4cbdac98b18851833b3acff74e7d136f848`, and invoked as:

```bash
/usr/bin/timeout 45s env \
  TMPDIR=/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g2_a90920a4741b31ba7cca01f43050f186/attempt-001/.review-tmp/custom \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  /projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g2_a90920a4741b31ba7cca01f43050f186/attempt-001/.review-tmp/independent_probes.py
```

It exited 0 in 3.53 seconds. Observed:

```text
layers: compressed_apply=true invalid_whiteout_pre_mutation=true
runner: marker_budgets=8/8 utf8_budget=true descendant_group_killed=true
state: cross_process_claim_outcomes=lost,won
images: cross_process_tag_race=conflict,success objects=1 leftovers=0
images: cross_process_same_content=success,success objects=1 leftovers=0
cli: domain_error_exit=2 stderr_single_line=true
independent_probes=PASS
```

The descendant check used a delayed marker in a disposable directory because process inspection was
outside the review sandbox. The absent marker showed that a grandchild remaining in the new process
group did not survive the timeout.

## Scratch cleanup

```bash
chmod -R u+w .review-tmp
find .review-tmp -depth -delete
test ! -e .review-tmp
```

All three commands exited 0. The final candidate inventory digest remained
`f65a641e38836de14a21804480007011b920123b7137c8fe36055f82df17c06b`.

## Setup observations and limitations

- A first export destination containing a literal `..` was rejected with `destination must not contain
  parent traversal`; the successful run used the required absolute destination above.
- A first harness run completed every assertion but its test-only `TemporaryDirectory` cleanup raced
  with a transient nonempty runtime and returned 1. Only the clean exit-0 rerun above is cited as
  passing evidence; final scratch removal was checked independently.
- The immutable review context could not create a shell here-document, so the harness was created via
  the workspace patch mechanism outside `CANDIDATE` and removed after capture.
- No upstream fetch, fuzzing, benchmark, profiler, transfer/deployment test, privilege, real namespace
  isolation, or hostile multi-tenant test was attempted. Factory-owned baseline and remediation
  inventories were unavailable. The results cover one POSIX/CPython 3.11.5 environment and assign no
  validation label.
