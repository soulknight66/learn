# Independent validation record

Date: 2026-08-31 (America/Chicago)

All candidate execution used argv-based runners and external wall-time caps. Builder scripts and
builder prose were treated as reproducible claims, not as completion evidence. The three review
files were written outside `CANDIDATE/`; no submitted file was edited.

The execution wrapper emitted unrelated UID/GID lookup warnings before shell commands. Those lines
are omitted below.

## Tool availability

Command:

```sh
for tool in cc gcc clang make python3 valgrind cppcheck jq git timeout; do
    command -v "$tool" || true
done
python3 --version
cc --version | sed -n '1,2p'
make --version | sed -n '1p'
ulimit -s
```

Observed:

```text
cc=/usr/bin/cc
gcc=/usr/bin/gcc
clang=UNAVAILABLE
make=/usr/bin/make
python3=/usr/bin/python3
valgrind=UNAVAILABLE
cppcheck=UNAVAILABLE
jq=UNAVAILABLE
git=UNAVAILABLE
timeout=/usr/bin/timeout
Python 3.6.8
cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
GNU Make 4.2.1
8192
```

## Immutable setup and builds

`CANDIDATE/` directories were mode 0555. A `cp -a` scratch copy retained those modes, so the first
build attempt exited 2 with `Cannot create temporary file in ./: Permission denied`. Only the copy
was then made writable:

```sh
scratch=$(mktemp -d -p "$PWD" .review-scratch.XXXXXX)
cp -a CANDIDATE "$scratch/candidate"
chmod -R u+w "$scratch/candidate"
timeout --signal=KILL 60s make -C "$scratch/candidate/starter" clean all
timeout --signal=KILL 60s make -C "$scratch/candidate/sealed/reference" clean all
```

Both post-copy builds exited 0. Observed compiler invocations used the submitted strict flags:

```text
cc -Iinclude -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror ...
cc -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror src/minic.c -o build/minic
```

Two clean rebuilds exited 0 and produced the same digest before and after:

```text
c67a6c46a41945ab748f087e96fbf4ece419968c9dd7810290c470504cb6dd35  starter/build/minic
278b0ef3c85e23dfc7386c289000e99ce89ff3d9ca36774a55aaf8fce8c9d370  sealed/reference/build/minic
```

## Supplied suites reproduced

Commands were run from the scratch candidate root:

```sh
timeout --signal=KILL 30s python3 -m unittest public_tests.test_process_control -v
timeout --signal=KILL 60s python3 public_tests/run_tests.py sealed/reference/build/minic
timeout --signal=KILL 120s python3 sealed/reference_tests/run_tests.py sealed/reference/build/minic
timeout --signal=KILL 20s sealed/reference/build/minic sealed/reference/examples/meta_vm.mc
timeout --signal=KILL 60s python3 public_tests/run_tests.py starter/build/minic
timeout --signal=KILL 30s python3 sealed/reference_tests/audit_pack.py
```

Observed results:

```text
process-control: Ran 4 tests; OK; exit 0
public/reference: 18 passed; 0 failed; exit 0
sealed/reference: 34 passed; 0 failed; exit 0
nested interpreter: stdout "42\n"; exit 0
public/starter: 12 passed; 6 failed; exit 1
audit: required_paths=23 missing=0 forbidden=0 special_files=0
       credential_hits=0 disclosure_violations=0; exit 0
```

The starter failures were the documented four successful-language cases, syntax diagnostic, and
step-limit behavior; all 12 CLI cases passed.

## Independent black-box matrix

A temporary reviewer harness used five-second per-case waits, new sessions, whole-group cleanup,
CPU/address-space/file/core/open-file limits, 131,072-byte capture limits, and a 90-second outer
deadline. It generated each fixture in a temporary directory and invoked only the built executable:

```sh
timeout --signal=KILL 90s python3 independent_probes.py
MINIC_EXE="$PWD/minic-o0" timeout --signal=KILL 90s python3 independent_probes.py
MINIC_EXE="$PWD/minic-o3-lto" timeout --signal=KILL 90s python3 independent_probes.py
```

The default `-O2`, separate `-O0`, and `-O3 -flto` executions each reported:

```text
SUMMARY passed=22 failed=1 total=23
FAIL valid-4097-call-sites expected_code=0 actual_code=65
diagnostic='too many function calls' timed_out=False truncated=False
```

The 22 passing probes covered comparison/boolean/call semantics, left-to-right effects,
short-circuiting, implicit zero return and initialization, compile-before-effects, runtime source
line, embedded NUL rejection, and exact/one-over identifier, parameter, local, function, frame,
operand-value, call-expression nesting, bytecode, and source-byte boundaries. In particular:

```text
operand-values-exact-8192: exit 0
operand-values-one-over: exit 70, "operand stack capacity exceeded"
bytecode-exact-65536: exit 0
bytecode-one-over: exit 65, "too many bytecode instructions"
source-bytes-exact-1048576: exit 0
source-bytes-one-over: exit 66, "input exceeds"
```

A focused independently generated call-site boundary probe observed:

```text
calls=4096 bytes=16414 tokens=16399 bytecode=8198 returncode=0 stdout='' diagnostic=''
calls=4097 bytes=16418 tokens=16403 bytecode=8200 returncode=65 stdout='' diagnostic='too many function calls'
```

Both inputs conform to the grammar and remain below every translation limit documented in
`REQUIREMENTS.md`. Inspection located the binding implementation-only capacity at
`MAX_PATCHES = 4096` and its rejection at `sealed/reference/src/minic.c:468-470`.

## Independent structure and metadata checks

A separate Python walk used `os.lstat`, strict JSON parsing with duplicate-key rejection, and common
private-key/AWS/GitHub/OpenAI credential signatures over every submitted regular file. Observed:

```text
regular_files=67 special_entries=0 credential_signature_files=0
answers_outside_sealed=0 c_sources_outside_starter_or_sealed=0
metadata_match project=True source=True commit=True snapshot=True
status=GENERATED labels=GENERATED,PARTIAL independent_validation=REQUIRED productionized=false
manifest_file_sha256=90e92288880bdd67f39044ad703d031800dc5b25687309f42ad0f1df007bd71d
provenance_file_sha256=7d163264fd18e6ecaf9a2efd9c23d95b0f16ad143aa02ac4eca6c14f26a89bb6
```

Candidate tree integrity command:

```sh
find CANDIDATE -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum
```

Observed before final review-file creation and again afterward:

```text
d7b3f5548a150a9d1fe583d345ac7f98e15d73a5e7ed2c79acde3e0e760949fb  -
```

## Inconclusive or unavailable checks

Sanitizer compile commands were attempted:

```sh
cc -std=c11 -O1 -g -Wall -Wextra -Wpedantic -Werror \
   -fsanitize=undefined -fno-sanitize-recover=all sealed/reference/src/minic.c -o minic-ubsan
cc -std=c11 -O1 -g -Wall -Wextra -Wpedantic -Werror \
   -fsanitize=address,undefined -fno-omit-frame-pointer \
   sealed/reference/src/minic.c -o minic-asan-ubsan
```

Both links exited 1: `libubsan.so.1.0.0` was missing, and the combined build also lacked
`libasan.so.5.0.0`. No sanitizer result is claimed. Clang, Valgrind, cppcheck, a second architecture,
the upstream resource, an exported learner view, and the builder's prior staged roots were not
available. No fuzzing, benchmarking, transfer verification, or production assessment was performed.
