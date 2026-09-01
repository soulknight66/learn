# Repair validation record

This record contains commands actually run in the allocated repair workspace on 2026-08-31. The
artifact remains `GENERATED` + `PARTIAL`; every result below is builder-authored evidence and fresh
independent validation is still required. Repeated ambient user/group name-resolution warnings from
the command wrapper are omitted from the transcripts.

## Runtime availability and JavaScript attempts

The default static-check interpreter is the older runtime that failed the prior checker. The repaired
utilities support it, and the separately provisioned newer interpreter remains available:

```text
$ python3 --version
Python 3.6.8
exit 0

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5
exit 0

$ timeout 5 node --version
timeout: failed to run command ‘node’: No such file or directory
exit 127
```

A PATH lookup for compatible JavaScript runtimes used this bounded-name loop:

```text
$ for runtime_name in node nodejs deno bun qjs js d8 jsc quickjs; do runtime_path=$(command -v "$runtime_name" 2>/dev/null); if [ -n "$runtime_path" ]; then printf '%s=%s\n' "$runtime_name" "$runtime_path"; else printf '%s=not-found\n' "$runtime_name"; fi; done
node=not-found
nodejs=not-found
deno=not-found
bun=not-found
qjs=not-found
js=not-found
d8=not-found
jsc=not-found
quickjs=not-found
exit 0
```

Each JavaScript attempt had a 30-second outer bound:

```text
$ timeout 30 node --test public_tests/*.test.mjs
timeout: failed to run command ‘node’: No such file or directory
exit 127

$ timeout 30 node --test sealed/reference_tests/*.test.mjs
timeout: failed to run command ‘node’: No such file or directory
exit 127

$ timeout 30 node sealed/adversarial/run.mjs
timeout: failed to run command ‘node’: No such file or directory
exit 127

$ timeout 30 node sealed/benchmarks/benchmark.mjs --samples 1 --iterations 1 --warmup 0
timeout: failed to run command ‘node’: No such file or directory
exit 127
```

No JavaScript file was parsed or executed. There is no JavaScript pass count, candidate/oracle
behavioral comparison, fuzz result, timing, or benchmark result. In particular, the static identity
records below are not a substitute for running the evaluator harness on Node.js 20+.

## Default-deny projected-view audit

The audit constructs each cumulative file set in memory, rejects symlinks and special paths, verifies
that later prompts are absent until their stage, verifies that `sealed/` is always absent, and binds
the result to sorted path/content hashes. It did not create a student workspace or materialized view.

```text
$ PYTHONDONTWRITEBYTECODE=1 timeout 20 python3 sealed/validation/view_policy.py audit
core files=25 sha256=4f29447b49455e0decd6a0f26c5fc5c60e895437eaaea0545f682e5d0201e846
debugging files=29 sha256=091bb90b13174034cfe721cbbff03c2d3613d41e0b483d2fa80b37e925fb800b
review files=33 sha256=c093c9d32852b096533ba58a8d411ffb09d315f81ef7b6aef15581cf23642d2a
adversarial files=34 sha256=e677361cf4fa6317cf9ee1e01e202af474424ebc8931d3f9a61fbb1ccf77986e
benchmarks files=35 sha256=6d03f851876c217512f6493d7484b2ee0e5ba6a7ae3dc00c9077adf5dfb7dfa3
VIEW POLICY AUDIT PASS
exit 0
```

The isolation and evaluator-binding unit tests also ran under Python 3.6.8:

```text
$ PYTHONDONTWRITEBYTECODE=1 timeout 20 python3 -m unittest discover -s sealed/validation -p 'test_*.py' -v
test_binding_records_candidate_and_oracle_identities (test_evaluator_wiring.EvaluatorWiringTests) ... ok
test_binding_uses_fixed_pack_relative_entries (test_evaluator_wiring.EvaluatorWiringTests) ... ok
test_evaluator_runners_do_not_bypass_the_binding (test_evaluator_wiring.EvaluatorWiringTests) ... ok
test_supplied_candidate_imports_stay_inside_starter (test_evaluator_wiring.EvaluatorWiringTests) ... ok
test_each_view_has_a_bound_identity (test_view_policy.ViewPolicyTests) ... ok
test_later_prompts_are_absent_until_revealed (test_view_policy.ViewPolicyTests) ... ok
test_no_view_exposes_sealed_or_administrator_files (test_view_policy.ViewPolicyTests) ... ok
test_stage_names_and_roots_are_cumulative (test_view_policy.ViewPolicyTests) ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.108s

OK
exit 0
```

This is a builder-side projection audit, not a `TRANSFER_VERIFIED` label. An administrator must still
materialize and independently inspect the selected view in the real delivery boundary.

## Complete-pack static validation

The checker rejects duplicate JSON keys, compares the manifest exactly, checks canonical immutable
metadata hashes, verifies required/forbidden paths and path types, resolves relative JavaScript
imports, checks the fixed evaluator wiring, audits every projected view, and scans all 74 artifact
files for a bounded set of high-confidence credential patterns.

```text
$ PYTHONDONTWRITEBYTECODE=1 timeout 20 python3 sealed/validation/check_artifact.py
required paths: 23/23 present
raw forbidden paths present: []
artifact forbidden paths present: []
artifact path types: regular files/directories only
metadata: strict JSON, exact manifest, immutable object hashes match
JavaScript modules: 27 files, 46 relative imports resolved
evaluator binding: fixed candidate and oracle entries with artifact identities
evaluator artifacts: algorithm=path-content-sha256-v1 candidate=c8014bfeaec5dcf7d7a9ae40a873a495f07806f608bef6aac9b08441d8c61ee1 oracle=ddb6c95a9e6c26dafa217e8f300cc589d77e56c11cb7e2b6103096a3f0ca1942
learner views: 5 default-deny cumulative stages audited; sealed paths absent
credential scan: 74 files, 0 high-confidence matches
STATIC VALIDATION PASS
exit 0
```

The same checker was actually rerun with the explicit Python 3.11.5 interpreter and produced the
same lines and exit status:

```text
$ PYTHONDONTWRITEBYTECODE=1 timeout 20 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/validation/check_artifact.py
required paths: 23/23 present
raw forbidden paths present: []
artifact forbidden paths present: []
artifact path types: regular files/directories only
metadata: strict JSON, exact manifest, immutable object hashes match
JavaScript modules: 27 files, 46 relative imports resolved
evaluator binding: fixed candidate and oracle entries with artifact identities
evaluator artifacts: algorithm=path-content-sha256-v1 candidate=c8014bfeaec5dcf7d7a9ae40a873a495f07806f608bef6aac9b08441d8c61ee1 oracle=ddb6c95a9e6c26dafa217e8f300cc589d77e56c11cb7e2b6103096a3f0ca1942
learner views: 5 default-deny cumulative stages audited; sealed paths absent
credential scan: 74 files, 0 high-confidence matches
STATIC VALIDATION PASS
exit 0
```

The credential scan is a deterministic pattern check, not a comprehensive secret audit. The static
pass does not establish JavaScript syntax, module loading, runtime correctness, security, or
performance.

## Staged-root preservation and prior-entry coverage

The content aggregate commands ran before copying and again after the repair; both observations for
each staged root were identical:

```text
$ find PRIOR_BUILD -type f -exec sha256sum {} + | sort | sha256sum
054698ff0c7734b8c1caa344647f71a95edf6f1bc607abb5c31fd2a1bfaaa1e4  -

$ find PRIOR_REVIEW -type f -exec sha256sum {} + | sort | sha256sum
219834a54fd789a131a49c12783ee707d0a59ef4a9c5fd2faed3aa781b779270  -
```

A read-only path/type comparison from every staged prior-build entry to its repaired top-level
counterpart used this command and observed:

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from pathlib import Path
source = Path('PRIOR_BUILD')
missing = []
type_mismatches = []
for staged in sorted(source.rglob('*')):
    relative = staged.relative_to(source)
    repaired = Path(relative)
    if not repaired.exists():
        missing.append(relative.as_posix())
    elif staged.is_file() != repaired.is_file() or staged.is_dir() != repaired.is_dir():
        type_mismatches.append(relative.as_posix())
print('prior_entries={}'.format(sum(1 for _ in source.rglob('*'))))
print('missing={}'.format(missing))
print('type_mismatches={}'.format(type_mismatches))
PY
prior_entries=104
missing=[]
type_mismatches=[]
exit 0
```

Separate `find` checks over the artifact roots printed no scratch bytecode, symlink, or special path:

```text
$ find starter public_tests environment sealed adversarial debugging review_exercises benchmarks -name '__pycache__' -o -name '*.pyc'
(no output)
exit 0

$ find starter public_tests environment sealed adversarial debugging review_exercises benchmarks \! -type f \! -type d -print
(no output)
exit 0
```

The two staged roots were not modified. Platform-owned workspace controls are outside the artifact
roots and were not treated as challenge-pack content.

## Claim boundary

The repaired pack contains implemented evaluator binding, projection policy, static/unit checks,
reference numeric-domain handling, and new test cases, but executable JavaScript validation remains
blocked by the missing runtime. No `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is claimed. `MANIFEST.yaml` remains exactly
`GENERATED` + `PARTIAL` with independent validation required.
