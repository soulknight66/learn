# Independent validation record

Date: 2026-08-31 (America/Chicago)  
Review workspace: `/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_review_v1_1863bc88c1a77e27040408cec497262d/attempt-001`  
Disposition: **REVISE**

`CANDIDATE/` was treated as immutable. Builds and generated fixtures were placed under the
reviewer's `_review_work/` scratch directory. The execution wrapper prefixed shell output with
unrelated UID/GID lookup warnings; those warnings are omitted from the result excerpts below.

## Toolchain

Command:

```sh
command -v cc || true
command -v gcc || true
command -v clang || true
command -v make || true
command -v python3 || true
python3 --version
cc --version | sed -n '1,2p'
ulimit -s
```

Observed:

```text
/usr/bin/cc
/usr/bin/gcc
/usr/bin/make
/usr/bin/python3
Python 3.6.8
cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
Copyright (C) 2018 Free Software Foundation, Inc.
8192
```

There was no `clang` result. The stack limit was 8,192 KiB.

## Immutable artifact and metadata audit

Commands:

```sh
find CANDIDATE -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum
find CANDIDATE -type f | wc -l
find CANDIDATE \( -type l -o -type p -o -type s -o -type b -o -type c \) -print
sha256sum CANDIDATE/PROVENANCE.json CANDIDATE/MANIFEST.yaml
```

Observed:

```text
4712c2025215c4db62fb3e08ade721d54e11078fb152ae852c315032c8b2e7b0  -
64
7d163264fd18e6ecaf9a2efd9c23d95b0f16ad143aa02ac4eca6c14f26a89bb6  CANDIDATE/PROVENANCE.json
90e92288880bdd67f39044ad703d031800dc5b25687309f42ad0f1df007bd71d  CANDIDATE/MANIFEST.yaml
```

The special-file query produced no paths. A strict JSON load with duplicate-key rejection
succeeded for both JSON-formatted metadata files. The following consistency check was run:

```sh
python3 - <<'PY'
import json
with open('CANDIDATE/MANIFEST.yaml') as f:
    manifest=json.load(f)
with open('CANDIDATE/PROVENANCE.json') as f:
    provenance=json.load(f)
checks={
 'project_id': manifest['project_id']==provenance['project']['project_id'],
 'source_id': manifest['source_id']==provenance['project']['source_id']==provenance['source']['source_id'],
 'source_commit': manifest['source_commit']==provenance['project']['metadata']['provenance']['source_commit']==provenance['source']['commit_hash'],
 'snapshot_hash': manifest['provenance_sha256']==provenance['snapshot_sha256'],
 'labels_conservative': manifest['status']=='GENERATED' and manifest['validation_labels']==['GENERATED','PARTIAL'] and manifest['productionized'] is False and manifest['independent_validation']=='REQUIRED',
}
for key in sorted(checks): print(key, checks[key])
PY
```

Observed:

```text
labels_conservative True
project_id True
snapshot_hash True
source_commit True
source_id True
```

A bounded grep for common private-key headers, access-token forms, and password/secret/API-key
assignments returned no hits. All `ANSWER.md`, reference implementation, reference-test, and
production files found by the structural query were below `CANDIDATE/sealed/`. The only C files
outside that tree were the three incomplete starter sources.

These are internal consistency and placement observations. The upstream resource was not
retrieved, and no external learner view was available to test filtering of `sealed/`.

## Reproducible builds in a review copy

The submitted tree was read-only, so the documented commands were exercised from a writable copy:

```sh
mkdir -p _review_work
cp -R CANDIDATE _review_work/repro-candidate
chmod -R u+w _review_work/repro-candidate
make -C _review_work/repro-candidate/starter clean all
make -C _review_work/repro-candidate/sealed/reference clean all
```

Both make invocations exited 0. The observed compiler invocations used exactly the submitted
strict flags:

```text
cc -Iinclude -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror -c src/main.c -o build/main.o
cc -Iinclude -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror -c src/source.c -o build/source.o
cc -Iinclude -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror -c src/interpreter.c -o build/interpreter.o
cc -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror build/main.o build/source.o build/interpreter.o -o build/minic
cc -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror src/minic.c -o build/minic
```

An additional direct build, used by the independent probes, was:

```sh
cc -ICANDIDATE/starter/include -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror \
  CANDIDATE/starter/src/main.c CANDIDATE/starter/src/source.c \
  CANDIDATE/starter/src/interpreter.c -o _review_work/starter-minic
cc -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror \
  CANDIDATE/sealed/reference/src/minic.c -o _review_work/reference-minic
sha256sum _review_work/reference-minic _review_work/starter-minic
```

Observed executable digests:

```text
a000d210a0e812b2f67450916247f8dfefce9f06e47be9bce425a8b1f69d7dd5  _review_work/reference-minic
00547cdeaf92d62c0110ccb9b47b1736ca8aa14635758816da186feba8fe1a64  _review_work/starter-minic
```

## Candidate-authored suites and demonstration

Commands, from `_review_work/repro-candidate/`:

```sh
python3 public_tests/run_tests.py sealed/reference/build/minic
python3 sealed/reference_tests/run_tests.py sealed/reference/build/minic
sealed/reference/build/minic sealed/reference/examples/meta_vm.mc
```

Observed: exit 0; the public runner reported `6 passed; 0 failed`, the sealed runner reported
`25 passed; 0 failed`, and the demonstration printed `42` followed by a newline. Every named case
was reported as `PASS`.

Command:

```sh
python3 public_tests/run_tests.py starter/build/minic
```

Observed: exit 1 and `0 passed; 6 failed`. The four successful-program fixtures received exit 65
and no output; the syntax and step cases also lacked their expected diagnostic fragments. This
matches the candidate's disclosed incomplete-starter result.

These scripts are builder-authored evidence and do not by themselves establish a completion
label.

## Independent semantic and limit probes

A reviewer-authored Python driver generated each source in a temporary directory, invoked the
review-built executable with argv arrays in a new session, used an eight-second timeout, killed
the process group on timeout, captured output, and disabled core files. Command:

```sh
python3 _review_work/probe_reference.py _review_work/reference-minic
```

The driver SHA-256 was
`68c88e5ecd611a0428fa626b29aeb13e2c6598ce9b96b3fbf088024e7b8de2f3`.

The independent semantic source combined uninitialized locals, implicit returns, nested calls
with visible effects, short-circuiting, signed division/remainder, comparisons, boolean
normalization, and a nonzero Mini-C `main` return. It exited 0 with exactly:

```text
0
0
1
2
3
0
1
-2
-1
-2
1
0
1
```

A separate divide-by-zero on source line 3 exited 70, emitted no stdout, and diagnosed
`line-fault.mc:3: division by zero`.

Deterministic generated capacity observations:

| Probe | Observed result |
|---|---|
| 1,048,576 source bytes | exit 0 |
| 1,048,577 source bytes | exit 66, `input exceeds 1048576 bytes` |
| 65,536 emitted instructions | exit 0 |
| 65,541 emitted instructions | exit 65, `too many bytecode instructions` |
| 128 / 129 functions | exit 0 / exit 65 `too many functions` |
| 32 / 33 parameters | exit 0 / exit 65 `too many function parameters` |
| 256 / 257 locals | exit 0 / exit 65 `too many locals in function` |
| 63 / 64 identifier bytes | exit 0 / exit 65 `identifier exceeds 63 bytes` |
| 8,192 / 8,193 simultaneous operand values | exit 0 with `8192\n` / exit 70 `operand stack capacity exceeded` |
| 256 / 257 active frames | exit 0 / exit 70 `function frame capacity exceeded` |
| 4,097 call patches | exit 65, `too many function calls` (an additional internal limit) |

No capacity success is promoted to a validation label; these are finite observations.

### Token-table boundary

The exact sources were generated from these formulas and invoked with an eight-second timeout:

```python
tokens_65535 = "int main(){int a;" + "0;" * 32760 + "!0;" + "return 0;}"
tokens_65536 = "int main(){int a;" + "0;" * 32762 + "return 0;}"
```

Observed:

```text
65535-language-tokens bytes 65550 returncode 0 stdout '' diagnostic ''
65536-language-tokens bytes 65551 returncode 65 stdout '' diagnostic 'too many tokens'
```

The implementation stores EOF in the same 65,536-entry array. The contract does not explicitly
say whether that synthetic marker is included in its advertised token count, so this is recorded
as a contract ambiguity and conventional off-by-one rather than fabricated as a conclusive
interpretation.

### Deep valid-parentheses failure

Exact focused command:

```sh
python3 - <<'PY'
import os, resource, signal, subprocess, tempfile
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
source='int main(){print('+'('*32760+'1'+')'*32760+');return 0;}'
with tempfile.TemporaryDirectory(prefix='deep-review-', dir='_review_work') as directory:
    path=os.path.join(directory, 'deep.mc')
    with open(path, 'w') as handle:
        handle.write(source)
    print('bytes', len(source), 'language_tokens', 65534, 'tokens_with_eof', 65535)
    for attempt in range(1, 4):
        process=subprocess.Popen(['_review_work/reference-minic', path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, start_new_session=True)
        try:
            stdout, stderr=process.communicate(timeout=8)
            print('attempt', attempt, 'returncode', process.returncode,
                  'stdout', repr(stdout), 'stderr', repr(stderr))
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            print('attempt', attempt, 'timeout')
PY
```

Observed:

```text
bytes 65550 language_tokens 65534 tokens_with_eof 65535
attempt 1 returncode -11 stdout '' stderr ''
attempt 2 returncode -11 stdout '' stderr ''
attempt 3 returncode -11 stdout '' stderr ''
```

Return code `-11` is termination by signal 11. The valid source is within the documented source
and token capacities, and its compiled body needs only six instructions. No required source or
runtime diagnostic was produced. During broader runs, 32,750 nested pairs were sensitive to
process stack layout (both exit 0 and signal 11 were observed), while the focused 32,760-pair
probe failed three of three times.

### Starter/reference CLI discrepancy

Command:

```sh
python3 - <<'PY'
import subprocess
case='CANDIDATE/public_tests/cases/arithmetic.mc'
for name, exe, budget in [
 ('starter-plus','_review_work/starter-minic','+1'),
 ('reference-plus','_review_work/reference-minic','+1'),
 ('starter-leading-space','_review_work/starter-minic',' 1'),
 ('reference-leading-space','_review_work/reference-minic',' 1')]:
    result=subprocess.run([exe,'--max-steps',budget,case], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, universal_newlines=True, timeout=5)
    print(name, 'exit', result.returncode, 'stderr', repr(result.stderr))
PY
```

Observed: both starter cases exited 65 after reporting `interpreter not implemented (budget=1,
bytes=75)`; both reference cases exited 64 with the usage diagnostic. Thus the starter accepted
both spellings while the reference rejected them.

## Runner containment inspection

Commands:

```sh
nl -ba CANDIDATE/public_tests/run_tests.py | sed -n '15,24p'
nl -ba CANDIDATE/sealed/reference_tests/run_tests.py | sed -n '17,26p'
```

Observed: each runner uses `subprocess.run`, an argv list, captured stdout/stderr, and a timeout.
Neither call uses `start_new_session`, `setsid`, a process-group kill/reap path, an output-size
bound, or an aggregate suite resource bound. This was a static finding; no intentionally lingering
process was launched.

## Unavailable checks

Commands:

```sh
cc -std=c11 -O1 -g -Wall -Wextra -Wpedantic -Werror \
  -fsanitize=undefined -fno-sanitize-recover=undefined \
  CANDIDATE/sealed/reference/src/minic.c -o _review_work/reference-ubsan
cc -std=c11 -O1 -g -Wall -Wextra -Wpedantic -Werror \
  -fsanitize=address -fno-omit-frame-pointer \
  CANDIDATE/sealed/reference/src/minic.c -o _review_work/reference-asan
```

Observed linker failures:

```text
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
collect2: error: ld returned 1 exit status
```

Therefore no sanitizer result is claimed. Clang, a second architecture, upstream-content access,
network checks, fuzzing, benchmarking, model checking, production validation, and transfer-view
verification were also unavailable or deliberately out of scope.

After recording the commands, outputs, and executable/driver digests above, the reviewer removed
the `_review_work/` scratch copy and build products. `CANDIDATE/` remained unchanged; only
`EVALUATION.json`, `REVIEW.md`, and this validation record are durable review outputs.
