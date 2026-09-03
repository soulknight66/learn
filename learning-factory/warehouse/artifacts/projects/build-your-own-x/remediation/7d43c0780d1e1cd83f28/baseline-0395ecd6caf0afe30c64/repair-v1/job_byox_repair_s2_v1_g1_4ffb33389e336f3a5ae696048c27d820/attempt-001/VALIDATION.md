# Validation record

Artifact status: `GENERATED` + `PARTIAL`  
Repair generation: 1  
Validation date: 2026-09-02

Commands were run from the challenge-pack root with a non-login Bash shell. The configured
toolchains were invoked by absolute path. Results below are observations from this repair workspace,
not promotion evidence and not copied prior results.

## Toolchains

Command:

```sh
/arm/tools/nodejs/node/22.21.0/linux64/bin/node --version
```

Observed result: exit 0, stdout:

```text
v22.21.0
```

Command:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed result: exit 0, stdout:

```text
Python 3.11.5
```

## Syntax and socket-free tests

Command:

```bash
javascript_count=0
while IFS= read -r javascript_source; do
  /arm/tools/nodejs/node/22.21.0/linux64/bin/node --check "$javascript_source" || exit 1
  javascript_count=$((javascript_count + 1))
done < <(find starter public_tests sealed benchmarks debugging review_exercises \
  -type f -name '*.js' -print | sort)
printf 'javascript_syntax: PASS (%s files)\n' "$javascript_count"
```

Observed result: exit 0, stdout:

```text
javascript_syntax: PASS (22 files)
```

Command:

```sh
/arm/tools/nodejs/node/22.21.0/linux64/bin/node \
  sealed/reference_tests/regressions.test.js
```

Observed result: exit 0. TAP reported 5 tests, 5 passed, 0 failed. The passing cases covered:

- GET, returned-handler, multi-route, fallback-HEAD, and explicit-HEAD supported-method fallthrough;
- explicitly gated isolation of parameters, JSON bodies, statuses, and headers;
- abort/destruction before parser entry and an abort recorded during listener installation;
- a stream error recorded before parser entry; and
- invalid UTF-8 input.

Command:

```sh
/arm/tools/nodejs/node/22.21.0/linux64/bin/node \
  --test-name-pattern='^(compose|compiled patterns|middleware prefixes|JSON middleware reports synthetic)' \
  sealed/reference_tests/reference.test.js
```

Observed result: exit 0. TAP reported 4 tests, 4 passed, 0 failed. Network-dependent tests were
excluded by the explicit name pattern.

Command:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -m unittest \
  sealed/reference_tests/test_learner_view.py -v
```

Observed result: exit 0:

```text
test_exact_comparison_rejects_an_extra_evaluator_path ... ok
test_exact_comparison_rejects_changed_learner_content ... ok
test_source_selection_is_limited_to_the_authoritative_allowlist ... ok

----------------------------------------------------------------------
Ran 3 tests

OK
```

The elapsed-time suffix was omitted above because it is not an acceptance metric. No learner view
was created: this production-repair job expressly forbids creating a student workspace. These unit
results test deterministic selection and exact-inventory comparison only; they do not establish
`TRANSFER_VERIFIED`.

## Network-suite attempts

Command:

```sh
/arm/tools/nodejs/node/22.21.0/linux64/bin/node --test public_tests/*.test.js
```

Observed result: exit 1. The test runner reported the `public_tests/framework.test.js` file group
failed (`ERR_TEST_FAILURE`), with 0 file groups passed and 1 failed.

Command:

```sh
SUBMISSION_ROOT=sealed/reference \
  /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test public_tests/*.test.js
```

Observed result: exit 1. The test runner again reported the `public_tests/framework.test.js` file
group failed (`ERR_TEST_FAILURE`), with 0 file groups passed and 1 failed.

Command:

```sh
/arm/tools/nodejs/node/22.21.0/linux64/bin/node --test sealed/reference_tests/*.test.js
```

Observed result: exit 1. TAP reported 3 JavaScript file groups: the socket-free regression group
passed; `abort-socket.test.js` and the network-bearing `reference.test.js` groups failed. Summary:

```text
# tests 3
# pass 1
# fail 2
```

The following bounded direct invocation exposed the environmental blocker hidden by the file-group
summaries:

```sh
/arm/tools/nodejs/node/22.21.0/linux64/bin/node \
  sealed/reference_tests/abort-socket.test.js
```

Observed result: exit 1, with the first failure:

```text
error: 'listen EPERM: operation not permitted 127.0.0.1'
code: 'EPERM'
```

Thus Node loaded and executed JavaScript, but this sandbox did not permit an ephemeral loopback
listener. The HTTP integration suite, real-socket abort regression, and benchmark remain unexecuted
to completion. A network-capable independent validator must rerun them.

## Structure, metadata, isolation selection, and credentials

Command:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B \
  environment/verify_artifact.py
```

Observed result: exit 0, stdout exactly:

```text
required_paths: PASS (24/24)
forbidden_paths: PASS (0 present)
file_types: PASS (54 regular files, 18 directories, 0 special entries)
learner_projection: PASS (21 regular files, 4 directories, 0 evaluator roots selected)
metadata_values: PASS (manifest and provenance canonical hashes)
credential_scan: PASS (54 regular files scanned)
```

The 24-path check contains all 23 authoritative required paths plus the learner-view projector. The
verifier inventories only canonical artifact roots, not the read-only `PRIOR_BUILD/` and
`PRIOR_REVIEW/` staging areas or factory-owned workspace metadata.

Command:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c \
  'import json; paths=["MANIFEST.yaml","PROVENANCE.json","starter/package.json","sealed/reference/package.json"]; [json.load(open(path, encoding="utf-8")) for path in paths]; print("json_parse: PASS (4 files)")'
```

Observed result: exit 0, stdout:

```text
json_parse: PASS (4 files)
```

Command:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c \
  'import os; prior=[]
for parent, dirs, files in os.walk("PRIOR_BUILD"):
    dirs.sort(); files.sort()
    prior.extend(os.path.relpath(os.path.join(parent, name), "PRIOR_BUILD") for name in files)
missing=[path for path in prior if not os.path.isfile(path)]
assert not missing, missing
print("prior_regular_paths_preserved: PASS ({} of {})".format(len(prior), len(prior)))'
```

Observed result: exit 0, stdout:

```text
prior_regular_paths_preserved: PASS (50 of 50)
```

`MANIFEST.yaml` and `PROVENANCE.json` retain the authoritative immutable values. No local artifact
inventory root was created: the factory supplies the content-addressed inventory externally.

## Claims and limitations

- The manifest remains exactly `GENERATED` + `PARTIAL`, requires independent validation, and keeps
  `productionized` false.
- No `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or
  `PRODUCTIONIZED` label is claimed.
- The projector and its unit tests are not evidence that a learner view was actually transferred.
  A harness-controlled validator must create and inventory that external view.
- The linked tutorial and its `NOASSERTION`-licensed contents were not fetched or checked. No
  originality or upstream-license verification claim is added.
- No benchmark or production-readiness result was produced.
