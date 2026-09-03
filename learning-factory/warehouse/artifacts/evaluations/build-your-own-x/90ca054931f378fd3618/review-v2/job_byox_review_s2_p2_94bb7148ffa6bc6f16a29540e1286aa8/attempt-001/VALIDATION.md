# Independent validation record

Date: 2026-09-03 (America/Chicago)

Workspace:

```text
/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_review_s2_p2_94bb7148ffa6bc6f16a29540e1286aa8/attempt-001
```

`CANDIDATE/` was treated as immutable. Builds ran in reviewer-created scratch copies with per-command timeouts. The original tree fingerprint was unchanged after all checks.

## Tools actually invoked

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version | sed -n '1p'
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld --version | sed -n '1p'
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/strings --version | sed -n '1p'
/usr/bin/make --version | sed -n '1p'
```

Observed:

```text
gcc (GCC) 15.2.0
Python 3.11.5
GNU ld (GNU Binutils) 2.43
GNU strings (GNU Binutils) 2.43
GNU Make 4.2.1
```

The configured GCC, Python, and Binutils tools needed for this review were available. The unrelated Java, Node, Go, ARM, AArch64, NASM, QEMU, GLib, Flex, and Bison roots were not needed and were not invoked. `rg` was unavailable, so file discovery used `find`; this did not limit the candidate checks.

## Immutability and metadata

```sh
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
sha256sum CANDIDATE/PROVENANCE.json CANDIDATE/MANIFEST.yaml
find CANDIDATE -type l -print
```

The aggregate command returned the same value before and after validation:

```text
ae7726f977d900729e0713a2f412f8235f6e37888def92e18750ac585b6ea0f4  -
```

File hashes:

```text
3dc7fc913794fd6c9205f6d0588d0a9c4370fb639ae6991b97b4f28aaff9d57a  CANDIDATE/PROVENANCE.json
65467d58c5d0aafa3bcc9160d5ebb6aa7a78416e57137d07672277ff4dea4586  CANDIDATE/MANIFEST.yaml
```

No symlink was printed. A strict-JSON cross-check confirmed matching project ID, source ID, source commit, and provenance snapshot ID.

The immutable permission bits were preserved by the first scratch copy, so its first `make` attempt failed at `mkdir build` with `Permission denied`. The reviewer then changed permissions only in the scratch copy:

```sh
mkdir .review-scratch-20260903
cp -a CANDIDATE/. .review-scratch-20260903/
chmod -R u+w .review-scratch-20260903
```

Normalized pre-build content fingerprints of source and copy both equaled:

```text
1bf5dbc006f466af539e0f1e72035ce25b89deb611b73c1e6323446996097140  -
```

## Normal builds and submitted checks

Commands below ran from `.review-scratch-20260903/`:

```sh
timeout 30s environment/check.sh
timeout 60s make -C starter clean all
timeout 30s env MICROC_BIN="$PWD/starter/build/emberc" \
  public_tests/run.sh --lexer-only
timeout 60s make -C sealed/reference clean all
timeout 30s env MICROC_BIN="$PWD/sealed/reference/build/emberc-ref" \
  public_tests/run.sh
timeout 60s sealed/reference_tests/run.sh
timeout 10s sealed/reference/build/emberc-ref \
  --tower sealed/reference/self/tower.ec
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/reference_tests/verify_pack.py
```

Observed results:

- Environment check: exit 0, pinned GCC/Python versions, `C17 syntax smoke check: PASS`.
- Starter: strict C17 build exit 0; 2 lexer checks passed and 7 compiler/VM checks were explicitly skipped.
- Reference: strict C17 build exit 0; public suite 9/9 passed.
- Sealed tests: direct VM executable reported `VM unit tests: 10 passed`; private suite 11/11 passed.
- Tower: exit 0, stdout exactly `4242\n`.
- Pack verifier: five reported checks passed.

These observations reproduce the submitted normal-build claims, but a builder-authored suite alone is not acceptance evidence.

## Sanitizer rerun

```sh
SAN_FLAGS='-std=c17 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer'
timeout 60s make -C sealed/reference clean all CFLAGS="$SAN_FLAGS"
timeout 60s make -C sealed/reference_tests clean all CFLAGS="$SAN_FLAGS"
export LD_PRELOAD=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libasan.so.8.0.0:/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64/libubsan.so.1.0.0
export ASAN_OPTIONS=detect_leaks=0:halt_on_error=1
export UBSAN_OPTIONS=halt_on_error=1
timeout 20s sealed/reference_tests/build/test_vm
timeout 30s env MICROC_BIN="$PWD/sealed/reference/build/emberc-ref" \
  public_tests/run.sh
timeout 60s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest -v sealed.reference_tests.test_private
```

Both sanitizer builds exited 0. Direct VM 10/10, public 9/9, and private 11/11 passed with no ASan/UBSan diagnostic. Leak detection was disabled, matching the submitted versioned-runtime preload workaround.

## Independent boundary harness

A bounded Python here-document generated each source in a scratch-local temporary directory and launched the reference with an argv array, captured streams, a four-second per-case timeout, and `check=False`. It asserted the expected result for these 23 named cases:

```text
checked add, checked subtract, checked multiply, checked negate,
division zero, remainder zero, minimum division, minimum remainder,
short circuit, 63-byte identifier, 64-byte identifier,
negative heap, negative argument, prior output retained,
budget one, budget two, 256 locals, 257 locals,
stack overflow diagnosed, code max accepted, code max rejected,
source max accepted, source max plus one rejected
```

Core invocation pattern and exact boundary constructors:

```py
result = subprocess.run(
    [str(BIN), *prefix, str(path)],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    timeout=4,
    check=False,
)
minimum = "(-9223372036854775807-1)"
locals_256 = "".join(f"int x{i};" for i in range(256))
locals_257 = "".join(f"int x{i};" for i in range(257))
stack_4097 = "1+(" * 4096 + "1" + ")" * 4096
code_at_limit = "print(0);" * 21844
code_over_limit = "print(0);" * 21845
base = b"int main(){}"
source_at_limit = base + b"/*" + b"x" * (1048576 - len(base) - 4) + b"*/"
```

Observed:

```text
adversarial semantic checks: 23 passed
zero-budget CLI observation: rc=2 stderr='invalid positive instruction budget: 0'
```

This deterministic smoke harness was not coverage-guided fuzzing and does not establish a `FUZZED` label.

## Deep-syntax failure

The following probe generated valid sources and invoked `--check` with a ten-second child timeout and core dumps disabled:

```py
for depth in (6000, 8000, 10000):
    source.write_text(
        "int main(){print(" + "(" * depth + "1" + ")" * depth + ");}",
        encoding="ascii",
    )
    result = subprocess.run(
        [str(binary), "--check", str(source)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        check=False,
    )
```

Normal-build observations:

```text
depth=6000 bytes=12021 rc=0 elapsed=0.011s stderr=''
depth=8000 bytes=16021 rc=-11 elapsed=6.410s stderr=''
depth=10000 bytes=20021 rc=-11 elapsed=7.436s stderr=''
```

The 8,000-depth case was repeated with the sanitizer build and `ASAN_OPTIONS=detect_leaks=0:halt_on_error=1:abort_on_error=1`:

```text
asan deep syntax: depth=8000 bytes=16021 rc=-6
ERROR: AddressSanitizer: stack-overflow
```

This is a reproduced contract failure: the source is valid, well below the size ceiling, and does not approach a bytecode, local, operand-stack, heap, or instruction limit during `--check`.

## Diagnostic contract probe

```py
for name, args in (
    ("runtime", ["public_tests/cases/bad_overflow.ec"]),
    ("compile", ["--check", "public_tests/cases/bad_duplicate.ec"]),
):
    result = subprocess.run(
        [binary, *args], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=5, check=False,
    )
    print(name, result.returncode, repr(result.stdout), repr(result.stderr))
```

Observed:

```text
runtime rc=1 stdout='' stderr='runtime error: signed arithmetic overflow (line 3, column 19)\n'
compile rc=1 stdout='' stderr="public_tests/cases/bad_duplicate.ec:3:9: duplicate declaration 'value'\n"
```

Only the compile error conforms to the required leading `path:line:column:` prefix.

## Cross-directory reproducibility

After restoring normal flags, the reference was built cleanly from two otherwise identical source copies:

```sh
mkdir .review-repro-20260903
cp -a CANDIDATE/sealed/reference .review-repro-20260903/reference
chmod -R u+w .review-repro-20260903
timeout 60s make -C .review-scratch-20260903/sealed/reference clean all
timeout 60s make -C .review-repro-20260903/reference clean all
sha256sum .review-scratch-20260903/sealed/reference/build/emberc-ref \
  .review-repro-20260903/reference/build/emberc-ref
```

Observed:

```text
d19e328a142fe36a2855f13461e5112a3ff762f677ecfc647a6bcb7bc7128f40  first emberc-ref
517301cf96e327cd1722b82dc15304262ef0df5dd861533fbd8141549213c59e  second emberc-ref
cross-directory rebuild: DIFFERENT
```

Pinned GNU `strings` found the respective absolute build directory in each binary, consistent with unnormalized `-g` metadata. No bit-reproducible binary claim appears in the manifest.

## Archive, provenance, and disclosure checks

An independent full-tree walk, rather than only the submitted verifier's managed-path list, counted entry types and searched every file for private-key headers, AWS key IDs, GitHub token forms, and quoted password/API-key assignments:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
from pathlib import Path
import re, stat

root = Path("CANDIDATE")
patterns = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(rb"(?i)\b(?:api[_-]?key|password)\s*[:=]\s*[\"'][^\"'\r\n]{8,}"),
]
entries = list(root.rglob("*"))
files = sorted(path for path in entries if path.is_file())
non_regular = [path for path in entries if not (
    stat.S_ISREG(path.lstat().st_mode) or stat.S_ISDIR(path.lstat().st_mode)
)]
hits = [path for path in files for pattern in patterns if pattern.search(path.read_bytes())]
print(f"full-tree archive check: files={len(files)} "
      f"non_regular={len(non_regular)} credential_hits={len(hits)}")
PY
```

```text
full-tree archive check: files=61 non_regular=0 credential_hits=0
```

The only GitHub URL found was the declared upstream reference in `PROVENANCE.json`. Manifest/provenance cross-links passed. The external catalog snapshot and baseline were not present, and network access was restricted, so external provenance and originality were inconclusive.

`starter/`, `public_tests/`, and `environment/` contain no textual sealed/reference path references. The submitted pack nevertheless contains readable sealed answers, tests, and source beside learner material. No student-view projection or exclusion validator is included; that boundary must be proven by the orchestrator before publication.

## Limitations

- One pinned GCC/x86_64 environment only; no transfer or cross-toolchain validation.
- No network verification of upstream metadata, license evidence, or originality.
- No coverage-guided fuzzing, benchmark, leak check, or production assessment.
- The submitted tests are useful but remain builder-controlled evidence, not an acceptance label.
- This advisory review did not and cannot publish `REVIEWED`.
