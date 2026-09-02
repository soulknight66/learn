# Independent validation record

Review date: 2026-09-02 (America/Chicago)  
Candidate: read-only `CANDIDATE/`  
Disposition: `REVISE`

All commands ran from the review workspace root. Builds and mutation-based tooling tests used
`.review-work/`; nothing was written under `CANDIDATE/`. The launcher prepended account-mapping
warnings from `/usr/bin/id` to command output; those warnings were environmental and are omitted
below. An exit status is zero unless another status is stated.

## Toolchain observations

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5

env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
  /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-x86_64 --version
qemu-x86_64 version 9.1.1

/usr/bin/as --version
GNU assembler version 2.30-123.el8

/usr/bin/ld.bfd --version
GNU ld version 2.30-123.el8

/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
openjdk version "21.0.5" 2024-10-15 LTS

/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-as --version
GNU assembler (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 2.45.1.20251203

/usr/bin/uname -s -m
Linux x86_64
```

Invoking QEMU without the configured GLib path failed before startup with an undefined
`g_date_time_format_iso8601` symbol. The exact configured GLib root above made it usable. Pinned
Python and QEMU were relevant configured tools. Java and Arm assembly were available but
inapplicable. No configured x86-64 binutils root was supplied, so the build necessarily used the
regular host files `/usr/bin/as` and `/usr/bin/ld.bfd`.

## Static structure and metadata

```text
env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 CANDIDATE/environment/audit.py
```

Observed:

```json
{"credential_patterns": 4, "files_scanned": 37, "forbidden_absent": 21, "manifest_exact": true, "provenance_object_exact": true, "required_regular": 37, "special_entries_absent": true}
```

An independent pinned-Python pass parsed `MANIFEST.yaml` and `PROVENANCE.json`, compiled all six
Python files in memory, and recomputed the canonical provenance-object digest. It reported:

```json
{"canonical_provenance_sha256":"dc759cd6068016565adafc56a86680e216fda2867ba90aed0c352f07ff2a6017","manifest_status":"GENERATED","productionized":false,"project_id_matches":true,"python_compiled":6,"regular_files":37,"snapshot_id_matches":true,"validation_labels":["GENERATED","PARTIAL"]}
```

Filesystem inspection found only regular files and directories, no symlinks or other special
entries. A targeted scan found the sole external source URL in `PROVENANCE.json`; no private-key,
AWS-key, or GitHub-token pattern matched. These narrow scans do not prove that arbitrary secrets are
absent.

## Reproducible build and ELF checks

```text
mkdir .review-work
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/environment/build.py CANDIDATE/sealed/reference/forth.S \
  -o .review-work/reference-a
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/environment/build.py CANDIDATE/sealed/reference/forth.S \
  -o .review-work/reference-b
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/environment/build.py CANDIDATE/starter/forth.S \
  -o .review-work/starter-cinder
/usr/bin/sha256sum .review-work/reference-a .review-work/reference-b \
  .review-work/starter-cinder
```

All three builds returned zero. Observed hashes:

```text
5b73caee22ee3e317b10049367130fcfb23a4973bff821c38f928cf2b9218e98  .review-work/reference-a
5b73caee22ee3e317b10049367130fcfb23a4973bff821c38f928cf2b9218e98  .review-work/reference-b
72a0205dee22854aa726e476e3e61f01886d037a1aa324b2169034e1c3c017ff  .review-work/starter-cinder
```

A third reference build used the copied source
`.review-work/candidate-copy/sealed/reference/forth.S` and output directory
`.review-work/alternate-output/`; it had the same reference hash and `cmp -s` returned zero.
`strings -a` found none of `cinder-build`, `attempt-001`, `candidate-copy`, or `reference/forth`.

Commands used for binary inspection:

```text
/usr/bin/file .review-work/reference-a .review-work/starter-cinder
/usr/bin/readelf -W -h .review-work/reference-a
/usr/bin/readelf -W -l .review-work/reference-a
/usr/bin/readelf -W -s .review-work/reference-a | /usr/bin/grep '_start$'
/usr/bin/readelf -d .review-work/reference-a
```

The reference was a statically linked x86-64 `ET_EXEC`, entry point `0x4000e8`, with global `_start`
at that address, no dynamic section, and `GNU_STACK` flags `RW` (not executable).

## Candidate-authored test suites

```text
env CINDER_BIN=.review-work/reference-a PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s CANDIDATE/public_tests -v

env REFERENCE_BIN=.review-work/reference-a PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s CANDIDATE/sealed/reference_tests -v

cp -R CANDIDATE .review-work/candidate-copy
chmod -R u+w .review-work/candidate-copy
env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s .review-work/candidate-copy/environment -p 'test_*.py' -v
```

The writable copy was required because the tooling regressions intentionally create and mutate
temporary fixtures. Results:

```text
Public:    Ran 10 tests in 0.020s — OK
Sealed:    Ran 13 tests in 0.048s — OK
Tooling:   Ran  6 tests in 1.386s — OK
```

Every named test reported `ok`; none skipped. A post-suite audit of the copy returned the same
37-file success object, and no tooling fixture or bytecode cache remained.

## Independent behavioral checks

A bounded pinned-Python subprocess wrapper gave the native reference
`: square dup * ; 12 square .\n`; it returned zero with stdout `144\n` and empty stderr. The starter
on empty input returned 2 with empty stdout and exactly
`error: interpreter not implemented\n` on stderr.

The reviewer harness ran 22 independently chosen cases. They covered all ASCII control-byte
separators, EOF comments, `#` inside a token, signed endpoints, name syntax, case sensitivity,
nested control flow, recursion, low-byte emission, stack rotation, representative failures, the
65,537-byte rejection, and a deterministic randomized program. The Python model calculated 880
expected wrapping-arithmetic, signed-division/remainder, comparison, and bitwise output lines.

Observed summary (harness exit 1 because failures are review findings):

```json
{"cases":22,"failed":2,"passed":20,"failures":[{"name":"overflow_prefix_suffix_name","actual_rc":2,"actual_stderr":"error: invalid definition\n","actual_stdout":"","expected_rc":0,"expected_stdout":"7\n","timeout":false},{"name":"negative_overflow_prefix_suffix_name","actual_rc":2,"actual_stderr":"error: invalid definition\n","actual_stdout":"","expected_rc":0,"expected_stdout":"8\n","timeout":false}]}
```

The deterministic randomized arithmetic case itself passed all 880 modeled results. A minimal
reproducer used `subprocess.run([binary], input=source, capture_output=True, timeout=3)` for:

```text
: 9223372036854775808x 7 ; 9223372036854775808x .
: -9223372036854775809x 8 ; -9223372036854775809x .
```

Each token is within the 31-byte name bound and has a nondigit suffix, so neither has the integer
shape defined by `REQUIREMENTS.md`. Both runs nevertheless returned 2 with
`error: invalid definition\n`.

## QEMU and benchmark smoke checks

QEMU required this environment and argv form:

```text
env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
  /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-x86_64 .review-work/reference-a
```

Results at a three-second process-group timeout were mixed. The first smoke timed out and was killed
with no output. A bounded `-strace` diagnostic rerun of the starter, empty reference, and square
smoke all completed in under 0.06 seconds with expected results. Three later non-strace repetitions
produced one timeout followed by two status-0 runs writing `144\n` (about 1.073 s and 0.061 s).
Accordingly, QEMU availability was demonstrated, but the candidate's three-second smoke is flaky in
this environment and no transfer result is inferred.

```text
env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/benchmarks/run.py .review-work/reference-a \
  --iterations 3 --terms 10 --timeout 3
```

The command returned zero and emitted `iterations: 3`, `terms_per_process: 10`, minimum
`1130779 ns`, median `1432109 ns`, maximum `11454184 ns`, and
`validation_label: UNVALIDATED_MEASUREMENT`. This only checks harness operation and supports no
performance conclusion or `BENCHMARKED` label.

## Disclosure, provenance, and claim review

- All implementation answers, the complete reference, reference tests, evaluator review, and
  production notes are under `sealed/`; no implementation answer was found in `starter/` or
  `public_tests/`.
- The manifest remains exactly `GENERATED`/`PARTIAL`, requires independent validation, and sets
  `productionized` false. The candidate explicitly disclaims all stronger labels.
- `LICENSE_BOUNDARY.md` distinguishes the CC0 catalog metadata from the linked resource's
  `NOASSERTION` license. The upstream snapshot/link was unavailable, so source hashes, license
  evidence, similarity, and clean-room authorship were not independently verified.
- Actual omission of `sealed/` from a learner transfer is controlled outside this workspace and was
  not transfer-verified.
- The benchmark is labeled unvalidated, and no fuzzing or production-readiness claim is made.

## Cleanup and integrity

After executable checks, the exact reviewer scratch directory `.review-work/` was removed. A final
inventory confirmed that only `CANDIDATE/`, `.agents/`, `.codex/`, `.factory-workspace`, and the three
review artifacts remained:

```text
/usr/bin/rm -r -- .review-work
```

The removal returned zero. Recomputing the deterministic candidate content aggregate produced
`aac1260cf08540a1fd96ed0647eecaac4cd052cb5b1ac9ba307b3c42b50c227e`, exactly matching the value
recorded before executable checks; no file under `CANDIDATE/` changed.
