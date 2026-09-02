# Independent validation record

Review date: 2026-09-02. Commands began in the review workspace root. `CANDIDATE/` was mounted read-only and was never edited. Repeated launcher warnings that `/usr/bin/id` could not resolve the numeric user/group names were environmental and did not affect command exit status.

## Toolchains

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed exit 0:

```text
Python 3.11.5
```

```bash
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
```

Observed exit 0:

```text
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
```

Java was available but was not useful for this standard-library Python artifact. `rg --files CANDIDATE` and `git status --short` each exited 127 because `rg` and `git` were unavailable on `PATH`; subsequent inventory and audit commands used `find`, `grep`, and the configured Python binary.

## Immutable input and runtime preflight

The initial path/content aggregate over every regular candidate file reported:

```text
files=64 sha256=84d83f6ba2b7ff94bdfdf50687ebb16143544083d13150a143a8acb27f903033
```

Running the documented preflight directly in the immutable review mount was intentionally unavailable:

```bash
cd CANDIDATE
TMPDIR=environment /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/check_runtime.py
```

Observed exit 2:

```text
error: temporary directory is not writable: [Errno 2] No usable temporary directory found in ['environment', '/tmp', '/var/tmp', '/usr/tmp', '<workspace>/CANDIDATE']
```

`CANDIDATE/` and `CANDIDATE/environment/` had read/execute-only directory modes. To exercise code without mutating the submission, a scratch directory was created with `mktemp -d -p . review-scratch.XXXXXX`, `CANDIDATE/` was recursively copied into it, and only the copy was made owner-writable. Before and after testing, all 64 copied files matched the immutable source byte-for-byte.

From that scratch copy:

```bash
TMPDIR=environment /usr/bin/timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/check_runtime.py
```

Observed exit 0:

```text
runtime_ok python=3.11.5 tempdir=<review-scratch>/CANDIDATE/environment
```

## Supplied test suites

Commands ran from the writable byte-identical scratch copy with bytecode writes disabled and outer timeouts. Candidate CLI tests also use captured argv-array subprocesses with five-second timeouts.

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=environment PYTHONPATH=sealed/reference \
  /usr/bin/timeout 30s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v
```

Observed exit 0:

```text
Ran 24 tests in 0.504s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=environment PYTHONPATH=sealed/reference \
  /usr/bin/timeout 45s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/reference_tests -v
```

Observed exit 0:

```text
Ran 66 tests in 1.118s
OK
```

The sealed run covered artifact structure; manifest/provenance fixtures; reader locations and ceilings; evaluator, closure, data, and built-in semantics; 6,000 tail calls; controlled non-tail exhaustion; CLI failures; compiler/VM differential and malformed programs; learner-view export; and exercise focus.

The intentionally incomplete learner starter was measured separately:

```bash
TMPDIR=environment PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  /usr/bin/timeout 30s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'import io, unittest; suite=unittest.defaultTestLoader.discover("public_tests"); result=unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite); print(f"tests_run={result.testsRun} failures={len(result.failures)} errors={len(result.errors)} successful={result.wasSuccessful()}")'
```

Observed reporting-command exit 0:

```text
tests_run=24 failures=5 errors=24 successful=False
```

This confirms incompleteness; it is not counted as a passing implementation run.

## Independent behavior probes

A reviewer-authored inline Python assertion program ran under the same reference `PYTHONPATH`, `TMPDIR`, and a 30-second outer timeout. It did not import candidate tests. Its 52 assertions covered:

- token locations, comments, adjacent delimiters, all major reader failures, canonical round trips, the exact 10,000-digit limit, and mixed list/quote nesting;
- arithmetic identities, truthiness, sequential `let`, left-to-right operator/argument effects, global `def`, lexical capture, callable equality, string/print behavior, all `empty?` value classes, and representative arity/type errors;
- 5,500 mutually tail-recursive calls, 5,200 calls through final `let`/`do`/`if` positions, unchanged host recursion limit, and controlled non-tail exhaustion; and
- four additional interpreter/VM differential programs, rejection of `def`/`let`/`fn`, boolean constant-index rejection, and invalid conditional targets.

Observed exit 0:

```text
independent_assertions=52 status=OK
```

The first draft of this reviewer probe exited 1 because the review assertion predicted a grouped rendering for interleaved list/quote syntax. The assertion was corrected to structural format/read round-trip; this was a reviewer-test error, not a candidate failure.

## Learner-view isolation

The exporter was invoked directly against immutable `CANDIDATE/`, writing only beneath the temporary review scratch root:

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/sealed/production/learner_view.py \
  CANDIDATE review-scratch.FPd46o/immutable-view
```

Observed exit 0:

```text
learner_view_files=20
```

An independent `pathlib` audit, not the exporter's `audit_view`, compared every output byte with its source and checked the allowlist, path kinds, modes, manifest labels, and normalized README license wording. Observed exit 0:

```text
learner_top=AGENTS.md,CONCEPTS.md,DESIGN_QUESTIONS.md,MANIFEST.yaml,README.md,REQUIREMENTS.md,environment,public_tests,starter files=20 dirs=4 byte_mismatches=0 bad_modes=0 instructor_entries=0 labels=['GENERATED', 'PARTIAL'] sha256=0703f6c7937a0052fbc26bcdd8a442455a2daa47d7119b866331e6728ba1a867
```

A second invocation with the same destination observed a controlled refusal, exit 2:

```text
error: destination already exists: <workspace>/review-scratch.FPd46o/immutable-view
```

Two early versions of the independent README assertion exited 1 because the reviewer script accidentally searched for an escaped backtick and then failed to normalize a Markdown line break. The corrected semantic text check passed as shown above.

No candidate file had multiple hard links, no cache/bytecode artifact appeared, and the immutable source contained no learner-writable file.

## Static, structural, and provenance audits

A reviewer-authored Python AST/filesystem audit parsed every Python file, collected absolute import roots from `starter/` and `sealed/reference/`, checked for Python dynamic execution, shell/process calls in implementation code, `shell=True`, credential-shaped text, symlinks, and special entries. It ran from the writable review root because a shell heredoc cannot create its temporary backing file in the read-only candidate directory.

Observed exit 0:

```text
python_files=33 parse_errors=[]
implementation_import_roots=['argparse', 'collections', 'dataclasses', 'pathlib', 're', 'sys', 'typing']
dangerous_implementation_calls=[] shell_true=[]
credential_hits=[] unusual_entries=[]
```

Canonical JSON and builder-style content fingerprints were recomputed from immutable input:

```text
manifest=0a134783939d3d2bd9fc51f0ab33ef43cb40e4c86dc52feceb41248b0886b18e
provenance=17238e9005ea6ad305702b2fd5f18b9693608e3ccf4bf89881f929bb46002422
fingerprint=f4934ef895e2ce82db31668cbd61191dc0ac27a179cb069f6a4e244eba64842b
files=64 labels=['GENERATED', 'PARTIAL'] productionized=False
```

Cross-field checks observed exit 0:

```text
identity_links=OK hash_shapes=OK catalog_license=CC0-1.0 linked_license=NOASSERTION linked_content_copied=False
```

The final immutable/copy comparison observed:

```text
original_files=64 original_sha256=84d83f6ba2b7ff94bdfdf50687ebb16143544083d13150a143a8acb27f903033
scratch_files=64 scratch_sha256=84d83f6ba2b7ff94bdfdf50687ebb16143544083d13150a143a8acb27f903033
added=[] removed=[] changed=[]
```

The temporary scratch copy and learner export were then explicitly removed; they were disposable validation products and are not recoverable from the workspace. The immutable `CANDIDATE/` remains the source of record.

## Limitations and label boundary

- No network or upstream snapshot was accessible. Source commit, catalog license evidence, linked-resource classification, baseline hashes, and non-copy/origin claims were not externally revalidated.
- `PRIOR_BUILD/` is not in the submitted candidate, so the builder's historical prior-pack byte comparison is not independently reproducible here.
- No fuzzing campaign, benchmark, profiler, external security assessment, transfer validation, or production validation was performed.
- The combined pack itself contains sealed answers. The exporter was validated, but only the delivery harness can enforce that learners receive its output rather than the combined tree.
- The direct preflight failure reflects the deliberate read-only reviewer mount; the byte-identical writable copy and exported learner directory passed it.

These results support only this advisory review. They do not modify `MANIFEST.yaml` or independently grant `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `TRANSFER_VERIFIED`, `PRODUCTIONIZED`, or `REVIEWED`.
