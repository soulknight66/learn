# Validation record

Validation date: 2026-08-31 (America/Chicago). Commands were run from the
challenge-pack root in this repair workspace. Results below were observed in
this repair generation; archived prior-build results are not used as evidence.
The login shell printed three user/group lookup warnings before commands. Those
host-account warnings are omitted from quoted program output.

## Environment

Command:

```bash
python3 environment/check_environment.py
```

Observed status 0:

```text
cc: cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
make: GNU Make 4.2.1
python3: Python 3.6.8
machine: x86_64
```

## Clean builds and learner baseline

Command:

```bash
make -C starter clean all
```

Observed status 0. The compilation used:

```text
cc -Iinclude -std=c11 -O2 -g -Wall -Wextra -Wpedantic -Werror -o mica src/mica.c
```

Command:

```bash
python3 public_tests/test_public.py
```

Observed status 1: 9 tests ran. The four tokenizer/diagnostic tests passed,
including the new whitespace-boundary and invalid-usage checks. Five tests that
need the deliberately absent parser/interpreter/compiler failed with the
documented starter diagnostic:

```text
mica: implementation error: parser and backend stages are not implemented
```

This is the expected incomplete learner baseline and is one reason the pack
remains `PARTIAL`.

Command:

```bash
make -C sealed/reference clean all
```

Observed status 0 with the same C11 warning-as-error flags.

## Repaired reference suites

Commands:

```bash
MICA_BIN=sealed/reference/mica python3 public_tests/test_public.py
MICA_BIN=sealed/reference/mica python3 sealed/reference_tests/test_reference.py
make -C sealed/reference check
```

All three returned status 0. The public suite reported 9/9 passing in 0.200s.
The direct sealed suite reported 15/15 passing in 0.767s. The Makefile wrapper
reran the same 15 tests and reported success in 0.591s. These are local,
pack-authored tests and do not establish an independent validation label.

The public additions exercise all four accepted whitespace bytes, rejection of
vertical tab and form feed at the specified byte column, and the no-argument
usage failure. The sealed addition checks five malformed CLI shapes for status,
streams, prefix, and line count.

## Direct CLI repair probe

Command:

```bash
python3 -c 'import subprocess; p=subprocess.run(["sealed/reference/mica"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=10); print("returncode={}".format(p.returncode)); print("stdout={!r}".format(p.stdout)); print("stderr={!r}".format(p.stderr)); print("stderr_lines={}".format(len(p.stderr.splitlines())))'
```

Observed status 0 for the probe and captured child result:

```text
returncode=2
stdout=''
stderr="mica: usage error: expected 'mica tokens FILE', 'mica run FILE', or 'mica compile FILE -o OUTPUT.s'\n"
stderr_lines=1
```

## Native smoke check

Command:

```bash
mkdir -p environment/.validation-tmp && sealed/reference/mica compile sealed/reference/examples/fibonacci.mica -o environment/.validation-tmp/fib.s && cc -no-pie environment/.validation-tmp/fib.s -o environment/.validation-tmp/fib && environment/.validation-tmp/fib
```

Observed status 0 and stdout:

```text
0
1
1
2
3
5
8
13
21
34
```

The two generated files and directory were removed after the check with:

```bash
test -d environment/.validation-tmp && rm -r environment/.validation-tmp
```

## Content inventory and projected learner view

Commands:

```bash
python3 sealed/integrity/update_inventories.py
python3 environment/verify_artifact.py
python3 environment/materialize_student_view.py .student-view-check
python3 environment/verify_student_view.py .student-view-check
python3 .student-view-check/environment/verify_artifact.py
```

All returned status 0. Inventory generation reported 18 hashed learner files
and 44 hashed complete-pack files; each inventory excludes only its own
self-referential JSON file. The complete-pack verifier observed:

```text
required-operational-paths: 45/45 regular files present
forbidden-paths: absent
symlinks-or-special-files: 0
learner-directory-forbidden-names: 0
metadata: strict JSON and exact expected objects
provenance-identifiers: manifest value is snapshot id; canonical-json sha256 89e2d6b2fddf6b8cd2a643e8f9290374bad176c3bc446ecbd23a7f9b21358808
artifact-content-inventory: 44/44 regular files match sha256
provenance-file-sha256: 6992abe93cba117def298c113e4277009b9c29d7ee93ff6bad71e8618d17972d (content-inventory checked)
credential-pattern-scan: no matches
```

Materialization reported 9 allowlisted roots and 19 regular files (18 hashed
files plus the self-excluded inventory). Both direct and projected copies of
the student verifier observed:

```text
student-view-top-level: 9/9 allowlisted entries only
student-view-symlinks-or-special-files: 0
student-view-forbidden-paths: 0
student-view-content-inventory: 18/18 regular files match sha256
student-view-manifest: exact GENERATED + PARTIAL object
student-view-credential-pattern-scan: no matches
```

The top level of that disposable view contained only the six allowlisted files
and `starter/`, `public_tests/`, and `environment/`; it contained no `sealed/`
entry. The view was removed with:

```bash
test -d .student-view-check && rm -r .student-view-check
```

This demonstrates the deterministic projection locally. It is builder-run
evidence, not proof that an external controller transferred this projection to
a learner, so no `TRANSFER_VERIFIED` claim is made.

## Integrity negative controls

After cleaning both binaries, the operational-completeness control used this
exact command block:

```bash
negative_path=.integrity-negative-control-mica.c
set -e
test ! -e "$negative_path"
mv starter/src/mica.c "$negative_path"
restore_negative_control() { mv "$negative_path" starter/src/mica.c; }
trap restore_negative_control EXIT
set +e
python3 environment/verify_artifact.py
negative_status=$?
set -e
restore_negative_control
trap - EXIT
printf 'negative-control-status=%s\n' "$negative_status"
test "$negative_status" -eq 1
```

The block returned 0 after confirming the inner verifier returned 1. It
reported both `missing required operational paths: starter/src/mica.c` and an
artifact-inventory path-set mismatch. The trap/restoration completed and the
source was present afterward.

The content-tamper control used:

```bash
backup_path=.integrity-negative-control-readme.md
set -e
test ! -e "$backup_path"
mv README.md "$backup_path"
cp PRIOR_BUILD/README.md README.md
restore_content_control() { rm README.md; mv "$backup_path" README.md; }
trap restore_content_control EXIT
set +e
python3 environment/verify_artifact.py
content_status=$?
set -e
restore_content_control
trap - EXIT
printf 'content-negative-control-status=%s\n' "$content_status"
test "$content_status" -eq 1
```

The block returned 0 after confirming the inner verifier returned 1 with
`artifact content mismatch: README.md`. The repaired README was restored.

## Informative unavailable sanitizer check

Command:

```bash
cc -Isealed/reference/include -std=c11 -O1 -g -Wall -Wextra -Wpedantic -Werror -fsanitize=address,undefined -fno-omit-frame-pointer -o environment/mica-sanitized sealed/reference/src/mica.c
```

Observed status 1:

```text
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
```

`test ! -e environment/mica-sanitized` then returned 0. No sanitizer run or
sanitizer-derived claim is made.

## Labels and limitations

All build products and disposable views were removed. No independent validator
was run by this worker. No `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`,
`REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is claimed.
`MANIFEST.yaml` remains exactly `GENERATED` + `PARTIAL`, requires independent
validation, and sets `productionized` to false.
