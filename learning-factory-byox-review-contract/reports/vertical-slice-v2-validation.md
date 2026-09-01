# Vertical-slice v2 validation

Date: 2026-08-30

The deterministic scheduler dispatched and completed these replacement jobs:

- `job_course_mit6s081_vertical_v2`
- `job_project_kvstore_vertical_v2`

Both artifacts use `tree-sha256-v2` and have `VERIFIED_V2` integrity records. The
course artifact is labeled `GENERATED+BUILDS+TESTED+TRANSFER_VERIFIED`. The project
artifact is deliberately labeled
`GENERATED+BUILDS+TESTED+FUZZED+BENCHMARKED+PARTIAL`; `PARTIAL` is retained because
its instrumented teaching implementation is not claimed to be production-ready.

## Independent replay

The published trees were copied to fresh temporary directories before replay so
the immutable warehouse copies and their recorded checksums were not changed.

The project command `python3.11 scripts/run_all.py` passed:

- 4 public tests and 10 recovery/bounds tests against the reference;
- the same 14 tests against the instrumented implementation;
- two fixed-seed, 600-operation model-fuzz runs;
- 6-thread by 80-operation stress;
- torn-tail recovery followed by compaction;
- failure reproduction against the intentionally buggy lost-delete variant;
- regression recovery against the reference; and
- one newly executed smoke benchmark with environment and raw timings captured.

The course commands `python3.11 examiner_only/grade_attempt.py` and
`python3.11 scripts/verify_isolation.py` passed all 8 public/hidden transfer tests
and confirmed that the student-safe tree contains no examiner paths, sealed
material, or symlinks.

## Promotion evidence

- Course artifact checksum:
  `caacd2b57e8562274d084920e1b125ad7f12519013e1f422624546b55c33e81d`
- Project artifact checksum:
  `4f9e86857fad6ba9de3dbdcbb2da9c2ba5253ff84be0939732a0f4554ed53889`

The authoritative commands, exit codes, validator claims, and paths are also
retained in SQLite and under the per-job warehouse logs.
