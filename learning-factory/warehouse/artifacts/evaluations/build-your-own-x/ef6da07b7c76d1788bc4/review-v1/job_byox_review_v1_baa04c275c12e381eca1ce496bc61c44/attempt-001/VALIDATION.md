# Independent validation record

Date: 2026-08-31 (America/Chicago)

All mutating commands ran in a disposable writable copy. `CANDIDATE/` was inspected and executed only with non-mutating commands; it was not repaired or relabeled. Candidate-authored suites are recorded as supporting evidence, not as validation-label proof.

## Host and immutable-input checks

Commands run from the review root:

```sh
sh CANDIDATE/environment/probe.sh
python3 -m json.tool CANDIDATE/MANIFEST.yaml >/dev/null
python3 -m json.tool CANDIDATE/PROVENANCE.json >/dev/null
python3 CANDIDATE/sealed/reference_tests/audit_pack.py
sha256sum CANDIDATE/PROVENANCE.json CANDIDATE/MANIFEST.yaml
find CANDIDATE -type f -exec sha256sum {} + | sort | sha256sum
find CANDIDATE -type f | wc -l
find CANDIDATE -type l -o -type b -o -type c -o -type p -o -type s
```

Observed:

- Exit 0 from the environment probe; `cc`, `make`, Python 3.6.8, and all declared command dependencies were found. Compiler was GCC 8.5.0.
- Both metadata files parsed as strict JSON. The submitted audit exited 0 with `AUDIT OK`.
- `PROVENANCE.json`: `2ade2f5c7ca0f0af11d436e0fc18422ffe831635622addace3c9a75e3ca7f374`.
- `MANIFEST.yaml`: `42d99873ff753f98b8ed8fe2fe18d771a90ae6e8dd75ff7bf5bd51edb65a3a41`.
- Aggregate over all submitted file hashes and paths: `8899c7982e7f1be65f82b60b840de076bf6dece10c6f97d42bf5cfa04da658d0`, both before and after testing.
- 51 regular files; no symlinks, devices, FIFOs, or sockets were found.

`rg`, `git`, `jq`, `clang`, `valgrind`, `cppcheck`, and `shellcheck` were unavailable. Searches used `find`, `sed`/inspection, hashes, and Python standard-library parsing where appropriate.

## Writable test copy

Setup:

```sh
review_dir=$(mktemp -d -p . .review-scratch.XXXXXX)
cp -a CANDIDATE "$review_dir/candidate"
chmod -R u+w "$review_dir/candidate"
cd "$review_dir/candidate"
```

The realized directory was `.review-scratch.EKmmtb`. The permission change applied only to the copy.

## Submitted build and test commands

Commands were bounded by outer `timeout` calls:

```sh
timeout 30 make -C starter clean all
timeout 30 make -C sealed/reference clean all
timeout 30 python3 public_tests/test_shell.py --shell sealed/reference/msh-reference -v
timeout 30 python3 public_tests/test_shell.py --shell starter/msh --stage invocation -v
timeout 60 make -C sealed/reference_tests clean test
```

Observed:

- Starter clean strict build: exit 0.
- Reference clean strict build: exit 0.
- Public/reference: 15 tests ran, all passed, exit 0.
- Starter invocation: 2 tests ran, both passed, exit 0.
- Parser unit binary: `parser_tests: 6 cases passed`.
- Job-table unit binary: `jobs_tests: 3 cases passed`.
- Integration: 11 tests passed.
- Adversarial: 4 tests passed.
- PTY interactive: 1 test passed.
- Full sealed command: exit 0.

These reproduce the submitted success record, but the scripts originate in the candidate and do not independently establish a `TESTED` label.

## Sanitizer availability

Command:

```sh
timeout 30 make -C sealed/reference clean all \
  CFLAGS='-std=c11 -O1 -g -Wall -Wextra -Wpedantic -Werror -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

Observed exit 2. All objects compiled, but linking failed with:

```text
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
```

A normal `make -C sealed/reference clean all` was then rerun and exited 0. Sanitizer results remain unavailable, exactly as the candidate states.

## Exercise and benchmark-driver reproduction

Commands:

```sh
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror \
  -o ../broken-demo debugging/pipe-eof/broken.c
timeout 1 ../broken-demo

cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror \
  -o ../fixed-demo debugging/pipe-eof/sealed/fixed.c
timeout 5 ../fixed-demo

cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror \
  -c -o ../review-candidate.o review_exercises/child-boundary/candidate.c

timeout 30 python3 benchmarks/run.py --shell sealed/reference/msh-reference --iterations 1
```

Observed:

- Broken EOF demo printed `payload` and timed out with 124.
- Fixed demo printed `payload` and exited 0.
- Review candidate compiled with exit 0; this is not a correctness result.
- Benchmark driver exited 0 and emitted one raw sample for each of its three scenarios plus the executable SHA-256. This was only a harness smoke check; no performance conclusion or `BENCHMARKED` label is claimed.

## Reviewer-owned probes

### Milestone isolation

The reference parser was linked with the unchanged starter executor and job module, without editing either submitted source tree:

```sh
cc -D_POSIX_C_SOURCE=200809L -Istarter/include \
  -std=c11 -O2 -g -Wall -Wextra -Wpedantic -Werror \
  -o ../stage1-parser-only-msh \
  starter/src/shell.c sealed/reference/src/parser.c starter/src/jobs.c

timeout 15 python3 public_tests/test_shell.py \
  --shell ../stage1-parser-only-msh --stage invocation -v
timeout 15 python3 public_tests/test_shell.py \
  --shell ../stage1-parser-only-msh --stage parsing -v
```

Observed: invocation passed 2/2. Parsing failed 3/3, exit 1. Every failure reported `msh: executor milestone is not implemented`; the syntax-recovery test also showed the correct unmatched-quote diagnostic. This isolates a test-stage dependency rather than a parser defect.

### Exact whitespace bytes

A Python standard-library driver invoked `msh-reference -c` three times, placing vertical tab (`0x0b`), form feed (`0x0c`), or carriage return (`0x0d`) between `a` and `b` in a single unquoted argument to `printf '<%s>\n'`.

Observed for each byte:

```text
exit=0 stdout=b'<a>\n<b>\n' stderr=b''
```

This demonstrates that `isspace` split each byte even though R2.1 lists only space, tab, and newline.

### Mixed stopped/completed jobs

A reviewer-owned C harness, outside `CANDIDATE`, initialized `msh_job_table`, added ID 1/PID 101 and ID 2/PID 202, marked ID 1 with an encoded `SIGTSTP` status, marked ID 2 with encoded exit 7, and called `msh_jobs_wait_all`. It was compiled and run as follows:

```sh
cc -D_POSIX_C_SOURCE=200809L -Icandidate/sealed/reference/include \
  -std=c11 -O2 -g -Wall -Wextra -Wpedantic -Werror \
  -o reviewer_wait_probe reviewer_wait_probe.c \
  candidate/sealed/reference/src/jobs.c
timeout 5 ./reviewer_wait_probe
```

Observed:

```text
msh: wait: remaining jobs are stopped
wait_result=1 retained=1
```

The highest-numbered completed retained job had status 7, exposing the R4.4 mismatch.

### Parse-before-launch

Command:

```sh
timeout 5 sealed/reference/msh-reference -c 'touch ../parse-side-effect |'
test ! -e ../parse-side-effect
```

Observed: shell exit 2, `msh: empty command in pipeline`, and the file remained absent.

### Initially closed standard input

Command:

```sh
python3 -c 'import os, subprocess; p=subprocess.run(
    ["sealed/reference/msh-reference", "-c", "printf x | cat"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    preexec_fn=lambda: os.close(0));
print("closed_stdin exit={} stdout={!r} stderr={!r}".format(
    p.returncode, p.stdout, p.stderr))'
```

Observed:

```text
closed_stdin exit=1 stdout=b'' stderr=b'cat: -: Bad file descriptor\ncat: closing standard input: Bad file descriptor\n'
```

## Limitations and non-claims

- The source catalog checkout, linked tutorial, and network were unavailable. The source commit, source snapshot digest, license evidence, and independent/no-copy assertion could not be externally corroborated.
- The manifest's `provenance_sha256` equals `PROVENANCE.json.snapshot_sha256`, not the SHA-256 of the provenance file. No source snapshot was available to recompute that identifier.
- The evaluator bundle contains sealed and evaluator-facing material, but no actual learner projection was supplied. Student-view exclusion and transfer safety are therefore inconclusive.
- No fuzzing, coverage, cross-platform run, deterministic failure injection, low-resource-limit run, PID-reuse test, extended terminal test, leak analysis, or production assessment was performed.
- No validation label was added or recommended solely from candidate-authored scripts or prose.
