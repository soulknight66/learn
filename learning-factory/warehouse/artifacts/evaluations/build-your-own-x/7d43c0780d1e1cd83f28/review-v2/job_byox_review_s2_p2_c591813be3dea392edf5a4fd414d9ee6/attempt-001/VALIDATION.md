# Independent validation record

Review date: 2026-09-02  
Candidate root: `CANDIDATE/`  
Advisory result: `REVISE`

`CANDIDATE/` was treated as immutable. Candidate-authored scripts were inspected and, where safe,
run only as structural probes; their output was not accepted as evidence for a promotion label.

## Toolchain discovery

Commands were run from `CANDIDATE/` with a non-login Bash shell unless another directory is stated.

```sh
node --version
```

Exit 127:

```text
/bin/bash: node: command not found
```

```sh
npm --version
```

Exit 127:

```text
/bin/bash: npm: command not found
```

The initial inventory tools were also unavailable:

```text
rg: command not found (exit 127)
git: command not found (exit 127)
```

`find`, `grep`, and SHA-256 inventories were used instead of `rg` and git status.

```sh
python3 --version
```

Exit 0:

```text
Python 3.6.8
```

```sh
python3 -c "import importlib.util; names=['esprima','tree_sitter','pyjsparser','quickjs','js2py']; print({name: bool(importlib.util.find_spec(name)) for name in names})"
```

Exit 0:

```text
{'esprima': False, 'tree_sitter': False, 'pyjsparser': False, 'quickjs': False, 'js2py': False}
```

No alternate JavaScript parser was available.

## Prescribed JavaScript suites

```sh
node --test public_tests/*.test.js
```

Exit 127: `/bin/bash: node: command not found`

```sh
SUBMISSION_ROOT=sealed/reference node --test public_tests/*.test.js
```

Exit 127: `/bin/bash: node: command not found`

```sh
node --test sealed/reference_tests/*.test.js
```

Exit 127: `/bin/bash: node: command not found`

No JavaScript implementation, test, fuzz target, or benchmark executed. The static files contain 5
public and 15 sealed `test(...)` declarations; that count came from the following source-only check
and is not a test result:

```sh
grep -c '^test(' public_tests/framework.test.js
grep -c '^test(' sealed/reference_tests/reference.test.js
```

Exit 0, respectively:

```text
5
15
```

## Structural probes

The candidate's own verifier was run to reproduce, not endorse, its recorded output:

```sh
python3 environment/verify_artifact.py
```

Exit 0:

```text
required_paths: PASS (23/23)
forbidden_paths: PASS (0 present)
file_types: PASS (50 regular files, 18 directories, 0 special entries)
metadata_values: PASS (manifest and provenance canonical hashes)
credential_scan: PASS (50 regular files scanned)
```

An ordinary `py_compile` attempt exited 1 because it tried to create
`environment/__pycache__` on the read-only candidate filesystem. It was replaced with a no-write
syntax check:

```sh
python3 -c "source=open('environment/verify_artifact.py','r').read(); compile(source,'environment/verify_artifact.py','exec'); print('python_compile_no_write: PASS')"
```

Exit 0:

```text
python_compile_no_write: PASS
```

```sh
python3 -c 'import json; [json.load(open(p)) for p in ["MANIFEST.yaml","PROVENANCE.json","starter/package.json","sealed/reference/package.json"]]; print("json_parse: PASS (4 files)")'
```

Exit 0:

```text
json_parse: PASS (4 files)
```

```sh
find . -xdev -type f | wc -l
find . -xdev -type l -print
find . -xdev \! -type f \! -type d -print
find . -xdev -type d | wc -l
```

The results were 50 regular files, no symlink output, no special-entry output, and 19 directories.
The directory count includes the candidate root and is therefore consistent with the candidate
verifier's count of 18 artifact directories below it.

## Independent metadata and dependency checks

From the review workspace root, this check loaded `CANDIDATE/MANIFEST.yaml`,
`CANDIDATE/PROVENANCE.json`, and both package files; compared project/source/commit fields; checked
labels and dependency-field absence; and calculated raw and canonical hashes:

```sh
python3 - <<'PY'
import hashlib
import json

root = 'CANDIDATE/'
manifest = json.load(open(root + 'MANIFEST.yaml'))
provenance = json.load(open(root + 'PROVENANCE.json'))
starter = json.load(open(root + 'starter/package.json'))
reference = json.load(open(root + 'sealed/reference/package.json'))

def canonical(value):
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()

dependency_keys = ('dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies')
checks = {
    'labels_exact': manifest['validation_labels'] == ['GENERATED', 'PARTIAL'],
    'not_productionized': manifest['productionized'] is False,
    'project_id_match': manifest['project_id'] == provenance['project']['project_id'],
    'source_id_match': manifest['source_id'] == provenance['source']['source_id'] == provenance['project']['source_id'],
    'source_commit_match': manifest['source_commit'] == provenance['source']['commit_hash'] == provenance['project']['metadata']['provenance']['source_commit'],
    'manifest_provenance_matches_snapshot': manifest['provenance_sha256'] == provenance['snapshot_sha256'],
    'starter_dependency_fields_absent': not any(key in starter for key in dependency_keys),
    'reference_dependency_fields_absent': not any(key in reference for key in dependency_keys),
}
print(json.dumps(checks, sort_keys=True))
print('manifest_canonical_sha256=' + canonical(manifest))
print('provenance_canonical_sha256=' + canonical(provenance))
print('provenance_raw_sha256=' + hashlib.sha256(open(root + 'PROVENANCE.json', 'rb').read()).hexdigest())
print('manifest_provenance_sha256=' + manifest['provenance_sha256'])
PY
```

It exited 0 with:

```text
{"labels_exact": true, "manifest_provenance_matches_snapshot": true, "not_productionized": true, "project_id_match": true, "reference_dependency_fields_absent": true, "source_commit_match": true, "source_id_match": true, "starter_dependency_fields_absent": true}
manifest_canonical_sha256=e2299a901563deda64a2679fbf65a36440bfbbc54206f834f3ce438dec98aab3
provenance_canonical_sha256=8830de4919fec4723ad5ea1219617b2d1c75a922aa1f3fe0e02152c6e90d9e1d
provenance_raw_sha256=0b89a7a1874b0b75c4f6835446a0ed19d24a90e86c9853ef1db680df4317d0f3
manifest_provenance_sha256=b4a3f7035cf40764fe4766026f9b3e7ca2cc04b97203df672a49e48a88493f00
```

```sh
grep -R -n 'require(' starter sealed/reference public_tests sealed/reference_tests benchmarks debugging review_exercises
```

Exit 0. Inspection of its output found only relative imports and these Node built-ins: `node:http`,
`node:util`, `node:assert/strict`, `node:path`, `node:test`, and `node:stream`.

```sh
grep -R -n -E 'node:child_process|child_process|eval\(|new[[:space:]]+Function|Function\(' \
  starter sealed/reference public_tests sealed/reference_tests benchmarks debugging review_exercises || true
```

Exit 0 with no output. The `|| true` wrapper makes the expected no-match result non-failing; the
meaningful observation is the empty match set.

## Progressive-disclosure and claim checks

```sh
find . -type f \( -path './sealed/*' -o -path '*/sealed/*' \) -print | sort
find . -type f \( -path './sealed/*' -o -path '*/sealed/*' \) | wc -l
```

The count was 18. It includes `sealed/reference/**`, `sealed/reference_tests/**`, design and production
notes, `debugging/content-length/sealed/ANSWER.md`, and
`review_exercises/request-isolation/sealed/ANSWER.md`. All are directly readable in the submitted
tree. No separate materialized learner view was supplied.

```sh
grep -R -n -E '\b(BUILDS|TESTED|FUZZED|BENCHMARKED|REVIEWED|TRANSFER_VERIFIED|PRODUCTIONIZED)\b' .
```

Exit 0 with matches only in `VALIDATION.md:73-74`, where the candidate explicitly denies those
claims. `MANIFEST.yaml` contains only `GENERATED` and `PARTIAL`, requires independent validation, and
sets `productionized` to false. Benchmark and productionization prose likewise make no result claim.

## Static correctness observations

All learner-facing code and prose, the full sealed reference, both test suites, and enrichment files
were read. Two source paths establish revision blockers without treating review prose as execution:

1. `sealed/reference/src/application.js:173-183` returns 405 for every nonempty allow set. It does not
   test whether the current method is allowed, so a matching GET route that delegates can end as 405.
2. `sealed/reference/src/body-json.js:38-110` checks `readableEnded`, then relies entirely on future
   abort/error/close events. It has no already-aborted/destroyed preflight, so parser entry after those
   events can remain pending.

These observations need Node-based regression tests after repair. Other runtime-sensitive behavior,
including invalid request targets, HEAD/error body suppression, post-header destruction, raw socket
aborts, and keep-alive framing, remains inconclusive.

## Candidate immutability

Before review-file creation, this command was run from the review workspace root:

```sh
find CANDIDATE -xdev -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

Observed aggregate of the sorted per-file hash list:

```text
5852d9696068e6434950100e5c5a01b3ec09d711b3310e61cdb6a144dcac8d48  -
```

After writing the review artifacts, the same command again produced:

```text
5852d9696068e6434950100e5c5a01b3ec09d711b3310e61cdb6a144dcac8d48  -
```

The final inventory remained 50 files, emitted no special entries, and contained no attempted
`environment/__pycache__`. Matching output demonstrates that no submitted regular-file content
changed.

## Limitations

- Missing Node/npm prevents any `BUILDS`, `TESTED`, `FUZZED`, or `BENCHMARKED` conclusion.
- Missing git and a JavaScript parser reduce independent checking to hashes, metadata parsing, and
  manual source review.
- The immutable source snapshot and linked tutorial are unavailable, so source license evidence,
  commit contents, and the no-copy assertion cannot be verified here.
- There is no learner-view artifact, transfer record, or orchestrator acceptance result. This review
  therefore cannot assign `TRANSFER_VERIFIED` or `REVIEWED`.
