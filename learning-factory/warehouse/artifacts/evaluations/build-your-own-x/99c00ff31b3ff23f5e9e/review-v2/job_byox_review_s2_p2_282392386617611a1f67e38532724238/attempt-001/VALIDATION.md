# Independent validation record

Date: 2026-09-02 (America/Chicago)

Verdict: **REVISE**. This is reviewer evidence only. It does not publish or
promote a `REVIEWED` or other validation label.

## Isolation and method

`CANDIDATE/` was treated as immutable. Execution occurred in a private copy:

```bash
test ! -e .review-sandbox
mkdir .review-sandbox
cp -a CANDIDATE .review-sandbox/candidate
chmod -R u+rwX .review-sandbox/candidate
```

The first build attempt preceded the `chmod`: `cp -a` retained the submitted
read-only directory modes, and both compiler invocations stopped before
compilation with `Cannot create temporary file in ./: Permission denied`.
Making only the scratch copy writable resolved that review-setup condition.
No command built in or modified `CANDIDATE/`.

Commands that could execute candidate code were wrapped in an outer `timeout`;
the supplied Python test cases also set per-child timeouts and use temporary
directories. Generated native programs were run only after the reference source
and generated assembly strategy had been inspected.

## Inventory, metadata, and hygiene

Commands:

```bash
find CANDIDATE -type f -printf '%p\t%s bytes\n' | sort
find CANDIDATE -type l -print
sha256sum CANDIDATE/MANIFEST.yaml CANDIDATE/PROVENANCE.json
```

Observed:

- 48 regular files and zero symlinks.
- `MANIFEST.yaml`: `ba3e84a7d6122a40394ede353841fc4d8396eff2a7adf7d4d7962bdf45711593`.
- `PROVENANCE.json`: `a923b5d3d1b9eddb2f2bc1fa7e93d5f28fe40ea8ef4727165ac9ad313ea0504d`.

Strict JSON parsing and cross-field check:

```bash
python3 - <<'PY'
import hashlib, json
m = json.load(open('CANDIDATE/MANIFEST.yaml'))
p = json.load(open('CANDIDATE/PROVENANCE.json'))
actual = hashlib.sha256(open('CANDIDATE/PROVENANCE.json', 'rb').read()).hexdigest()
print(m['project_id'] == p['project']['project_id'])
print(m['source_id'] == p['project']['source_id'] == p['source']['source_id'])
print(m['source_commit'] == p['project']['metadata']['provenance']['source_commit']
      == p['source']['commit_hash'])
print(m['provenance_sha256'] == p['snapshot_sha256'])
print(m['provenance_sha256'] == actual)
PY
```

Observed booleans, in order: `True`, `True`, `True`, `True`, `False`. Thus the
manifest value names the embedded snapshot digest, not the bytes of
`PROVENANCE.json`. The immutable baseline needed to recompute that snapshot
digest is not in the workspace.

Artifact verifier, from the scratch candidate root:

```bash
timeout 20s python3 sealed/reference_tests/verify_artifact.py
```

Observed exit status: 0.

```text
required regular files: 23/23
forbidden paths present: 0
symlinks or special files: 0
credential scan: 48 text files, 0 high-confidence hits
metadata: strict JSON, exact manifest, immutable file hashes verified
artifact verification: OK
```

The builder's `VALIDATION.md` records 49 text files for the purported final
tree. The submitted tree and independent verifier both report 48. Static
inspection also established that `EXPECTED_FILE_SHA256` authenticates only
`MANIFEST.yaml` and `PROVENANCE.json`, not the remaining payload.

## Toolchain and clean builds

Command, from the scratch candidate root:

```bash
timeout 20s python3 environment/check_toolchain.py
```

Observed exit status: 0.

```text
cc: /usr/bin/cc
  cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
make: /usr/bin/make
  GNU Make 4.2.1
python3: /usr/bin/python3
  Python 3.6.8
machine: x86_64
```

Commands:

```bash
timeout 60s make -C starter clean all
timeout 60s make -C sealed/reference clean all
```

Observed exit status: 0 for both. The starter compiled three C translation
units and linked `starter/pebble`; the reference compiled two translation units
and linked `sealed/reference/pebble`. Both used the documented strict warning
flags with `-Werror`.

## Supplied tests

Commands and observed results, from the scratch candidate root:

| Command | Exit | Observation |
| --- | ---: | --- |
| `timeout 60s python3 public_tests/run_tests.py` | 1 | 6/6 failed because the intentionally incomplete starter returns status 65; this matches its documentation. |
| `timeout 60s env PEBBLE_BIN="$PWD/sealed/reference/pebble" python3 public_tests/run_tests.py` | 0 | 6 tests, all `ok`, `OK` (0.184 s). |
| `timeout 60s env PEBBLE_BIN="$PWD/sealed/reference/pebble" python3 sealed/reference_tests/run_tests.py` | 0 | 10 tests, all `ok`, `OK` (0.810 s). |
| `timeout 60s env PEBBLE_BIN="$PWD/sealed/reference/pebble" python3 adversarial/run_tests.py` | 0 | 7 tests, all `ok`, `OK` (0.169 s). |

Passing builder-authored suites is a reproduced observation, not independent
proof of their coverage or grounds for a `TESTED` label.

## Independent semantic and differential check

An inline Python 3.6 driver used `random.Random(20260902)` to construct 250
fully parenthesized expressions of maximum generator depth five from signed
small integers, unary `-`/`!`, arithmetic, signed truncating `/` and `%`, and all
comparisons. It rejected zero divisors and replaced any generated magnitude
above 1,000,000,000 with equality. The driver computed each expected result
itself, wrote one program, and invoked these argv arrays with ten-second bounds:

```text
[sealed/reference/pebble, eval, oracle.pb]
[sealed/reference/pebble, compile, oracle.pb, -o, oracle.s]
[cc, oracle.s, -o, oracle]
[oracle]
```

It asserted exact `(status, stdout, stderr)` equality against the Python oracle
for both execution paths.

Observed exit status: 0.

```text
seeded oracle/differential expressions: 250/250 matched
```

This deterministic sample is independently designed but is neither exhaustive
nor evidence for a `FUZZED` label.

## Independent limit-boundary probes

An inline Python driver created each source in `TemporaryDirectory`, invoked
`[sealed/reference/pebble, eval, source]` with a ten-second timeout, and captured
both streams. Observed results:

| Probe | Status | Output/diagnostic |
| --- | ---: | --- |
| Left-deep expression tree, 128 literals | 0 | `128` |
| Left-deep expression tree, 129 literals | 65 | `expression tree exceeds 128 levels` |
| Parentheses nested 128 | 0 | `1` |
| Parentheses nested 129 | 65 | `expression nesting exceeds 128` |
| Blocks nested 128 | 0 | `1` |
| Blocks nested 129 | 65 | `block nesting exceeds 128` |
| 256 declarations followed by `print v255;` | 0 | `255` |
| 257 declarations | 65 | `program exceeds 256 variables` |

Two additional observations exposed contract/guidance issues:

```text
let x=1; let x=missing;
=> status 65, 1:16: unknown variable 'missing'

print (-9223372036854775807 - 1) % -1;
=> status 70, runtime error: arithmetic overflow
```

The first differs from the duplicate-first ordering taught in the sealed review
answer. The second behavior is required by a sealed test but is not stated in
the learner-visible requirements.

## Independent output-failure injection

The driver created a source containing 1,000 copies of
`print 1234567890;`, compiled and linked it using argv arrays, and ran both the
interpreter and native program with stdout opened on `/dev/full`; stderr was
captured and each child had a ten-second timeout.

Observed exit status for the driver: 0. Its observations were:

```text
stdout=/dev/full (required writing-failure status 66): eval=0 native=0
stdout=/dev/full stderr: eval='' native=''
```

This independently confirms the unchecked `printf`/flush path disclosed in
`sealed/REVIEW.md` and demonstrates violation of `REQUIREMENTS.md:13-15`.

## Subprocess containment audit

Command:

```bash
grep -R -nE 'start_new_session|setsid|killpg|process_group' \
  public_tests adversarial sealed/reference_tests benchmarks environment
grep -R -n 'subprocess.run' \
  public_tests adversarial sealed/reference_tests benchmarks environment
```

Observed: the first search returned no matches. The second found a
`subprocess.run` wrapper in each of the five runner areas. Their timeouts bound
the direct process in ordinary cases but do not establish or terminate process
groups, so descendants are not contained.

## Sanitizers and unavailable tools

Command:

```bash
timeout 60s make -C sealed/reference clean all \
  CFLAGS='-std=c11 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer'
```

Observed exit status: 2. Both objects compiled; link failed with:

```text
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
```

The ordinary reference build was restored successfully afterward. Tool lookup
also found `valgrind`, `clang`, `afl-fuzz`, `honggfuzz`, and `qemu-x86_64`
missing. No sanitizer execution, valgrind run, fuzzing, profiling, benchmark,
or cross-architecture test is claimed.

`git` and `rg` were also unavailable; read-only inventory and static searches
used `find`, `grep`, `sha256sum`, and direct inspection instead.

## Provenance and license limitations

The identifiers and commit fields are internally consistent, and the text
clearly keeps the CC0 catalog metadata separate from the linked resource's
`NOASSERTION` license. The source baseline and upstream checkout were not
available, and no network access was used. Consequently, the catalog waiver
evidence, upstream commit/content, source-line extraction, and no-copy claim
could not be independently verified. The generated-material phrase “for
personal educational use” is not an explicit redistribution license.

## Cleanup and review-output validation

Scratch build products were removed after the checks. The final reviewer files
were validated with strict JSON parsing, an exact-key/type check for the required
evaluation schema, and non-empty Markdown checks. `CANDIDATE/` still contained
the same 48 submitted regular files; its manifest was not edited.
