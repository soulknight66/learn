# Validation record

Artifact status: `GENERATED` + `PARTIAL`  
Repair generation: 2  
Validation date: 2026-09-02

All commands below were run from the challenge-pack root during this repair generation. Relevant
configured toolchains were invoked by absolute path. Test commands that could wait were bounded with
`/usr/bin/timeout`. These are builder observations, not independent acceptance or label-promotion
evidence.

## Toolchains

Commands:

```sh
/arm/tools/nodejs/node/22.21.0/linux64/bin/node --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed result: exit 0 for both commands:

```text
v22.21.0
Python 3.11.5
```

Node.js and Python were the only relevant configured toolchains for this dependency-free
CommonJS/Python pack. Availability of the other configured roots is not asserted.

## Syntax and socket-free suites

Command:

```bash
/usr/bin/timeout 20s bash -c 'javascript_count=0
while IFS= read -r javascript_source; do
  /arm/tools/nodejs/node/22.21.0/linux64/bin/node --check "$javascript_source" || exit 1
  javascript_count=$((javascript_count + 1))
done < <(find starter public_tests sealed benchmarks debugging review_exercises -type f -name "*.js" -print | sort)
printf "javascript_syntax: PASS (%s files)\n" "$javascript_count"'
```

Observed result: exit 0:

```text
javascript_syntax: PASS (22 files)
```

Command:

```sh
/usr/bin/timeout 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node \
  sealed/reference_tests/regressions.test.js
```

Observed result: exit 0. TAP reported 9 tests, 9 passed, 0 failed. In addition to the prior
socket-free regressions, the suite exercised:

- destruction after parser attachment with `complete === true`, bounded settlement, and listener
  cleanup;
- identity-only coding lists, malformed coding members, and mixed unsupported coding lists;
- removal of the defined entity/framing header set for 199, 204, and 304; and
- native `ServerResponse` serialization after stale transfer/content encoding state.

Command:

```sh
/usr/bin/timeout 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node \
  --test-name-pattern='^(compose|compiled patterns|middleware prefixes|JSON middleware reports synthetic)' \
  sealed/reference_tests/reference.test.js
```

Observed result: exit 0. TAP reported 4 tests, 4 passed, 0 failed.

Command:

```sh
/usr/bin/timeout 10s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -B -m unittest sealed/reference_tests/test_learner_view.py -v
```

Observed result: exit 0; 3 tests ran and all passed:

```text
test_exact_comparison_rejects_an_extra_evaluator_path ... ok
test_exact_comparison_rejects_changed_learner_content ... ok
test_source_selection_is_limited_to_the_authoritative_allowlist ... ok

OK
```

The allowlist test asserts that `environment/verify_artifact.py` is absent from source selection and
that the only selected environment entries are the directory, `README.md`, and `learner_view.py`.
No learner view was created by this production repair.

Command:

```sh
/usr/bin/timeout 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node \
  --test-name-pattern='^exports the documented' public_tests/framework.test.js
```

Observed result: exit 0. TAP reported 1 test, 1 passed, 0 failed.

## Reviewer-shaped remediation probes

The four probes that failed during the archived independent review were rerun against this repaired
reference.

Command:

```sh
/usr/bin/timeout 3s /arm/tools/nodejs/node/22.21.0/linux64/bin/node -e 'const {PassThrough}=require("node:stream");const tiny=require("./sealed/reference");const req=new PassThrough();req.headers={"content-type":"application/json"};req.complete=true;const parsing=tiny.json({limit:8})(req,{},()=>{});req.destroy();Promise.race([parsing.then(()=>"resolved",e=>"rejected:"+e.code),new Promise(r=>setTimeout(()=>r("pending"),100))]).then(outcome=>{const ok=outcome==="rejected:BODY_ABORTED";console.log("destroy_before_end:",ok?"PASS":"FAIL",outcome);process.exitCode=ok?0:1;});'
```

Observed result: exit 0:

```text
destroy_before_end: PASS rejected:BODY_ABORTED
```

Command:

```sh
/usr/bin/timeout 3s /arm/tools/nodejs/node/22.21.0/linux64/bin/node -e 'const http=require("node:http"),{Duplex}=require("node:stream"),{sendError}=require("./sealed/reference/src/application");let raw="";const socket=new Duplex({read(){},write(c,e,cb){raw+=c;cb()}});const res=new http.ServerResponse({method:"GET",httpVersionMajor:1,httpVersionMinor:1,shouldKeepAlive:false});res.assignSocket(socket);res.setHeader("transfer-encoding","chunked");res.setHeader("content-encoding","gzip");res.on("finish",()=>{const bad=/transfer-encoding: chunked/i.test(raw)&&/content-length: 58/i.test(raw)&&/content-encoding: gzip/i.test(raw);console.log("native_error_framing:",bad?"FAIL":"PASS",bad?"TE+CL and stale gzip emitted":"sanitized");process.exitCode=bad?1:0});sendError(res,Error("boom"));'
```

Observed result: exit 0:

```text
native_error_framing: PASS sanitized
```

Command:

```sh
/usr/bin/timeout 3s /arm/tools/nodejs/node/22.21.0/linux64/bin/node -e 'const {decorateResponse}=require("./sealed/reference/src/response");class R{constructor(){this.statusCode=200;this.headers=new Map;this.writableEnded=this.destroyed=false}setHeader(n,v){this.headers.set(n.toLowerCase(),String(v))}getHeader(n){return this.headers.get(n.toLowerCase())}hasHeader(n){return this.headers.has(n.toLowerCase())}removeHeader(n){this.headers.delete(n.toLowerCase())}end(){this.writableEnded=true}}const res=new R;decorateResponse(res,"GET");res.set("content-encoding","gzip").status(204).send("x");const bad=res.hasHeader("content-encoding");console.log("bodyless_entity_headers:",bad?"FAIL":"PASS",JSON.stringify(Object.fromEntries(res.headers)));process.exitCode=bad?1:0;'
```

Observed result: exit 0:

```text
bodyless_entity_headers: PASS {}
```

Command:

```sh
/usr/bin/timeout 3s /arm/tools/nodejs/node/22.21.0/linux64/bin/node -e 'const {PassThrough}=require("node:stream");const tiny=require("./sealed/reference");const req=new PassThrough;req.headers={"content-type":"application/json","content-encoding":"identity, identity"};req.complete=true;const parsing=tiny.json({limit:8})(req,{},()=>{});req.end("{}");parsing.then(()=>console.log("identity_encoding_list: PASS"),e=>{console.log("identity_encoding_list: FAIL",e.status,e.code);process.exitCode=1});'
```

Observed result: exit 0:

```text
identity_encoding_list: PASS
```

These local passes address the archived reproductions but do not confer an independent review
verdict.

## Structure, metadata, projection, and credentials

Command:

```sh
/usr/bin/timeout 10s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -B environment/verify_artifact.py
```

Observed result: exit 0:

```text
required_paths: PASS (24/24)
forbidden_paths: PASS (0 present)
file_types: PASS (54 regular files, 18 directories, 0 special entries)
learner_projection: PASS (20 regular files, 4 directories, 0 evaluator roots selected)
metadata_values: PASS (manifest and provenance canonical hashes)
credential_scan: PASS (54 regular files scanned)
```

This is the inspected builder-authored verifier's output, not a hidden-secret audit or an
orchestrator inventory. It inventories canonical artifact roots and intentionally excludes the
read-only staging roots and factory workspace metadata.

Commands:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import json; paths=["MANIFEST.yaml","PROVENANCE.json","starter/package.json","sealed/reference/package.json"]; [json.load(open(path,encoding="utf-8")) for path in paths]; print("json_parse: PASS (4 files)")'
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import json; m=json.load(open("MANIFEST.yaml")); p=json.load(open("PROVENANCE.json")); checks={"project_id":m["project_id"]==p["project"]["project_id"],"source_id":m["source_id"]==p["source"]["source_id"]==p["project"]["source_id"],"source_commit":m["source_commit"]==p["source"]["commit_hash"]==p["project"]["metadata"]["provenance"]["source_commit"],"snapshot_link":m["provenance_sha256"]==p["snapshot_sha256"]}; print(checks); assert all(checks.values())'
```

Observed result: exit 0 for both:

```text
json_parse: PASS (4 files)
{'project_id': True, 'source_id': True, 'source_commit': True, 'snapshot_link': True}
```

Command:

```sh
sha256sum MANIFEST.yaml PROVENANCE.json
```

Observed raw file hashes:

```text
604aa5df5e7dd82067bb8591aa638955360bc2bc363b0b8e06455e422a203fe4  MANIFEST.yaml
0b89a7a1874b0b75c4f6835446a0ed19d24a90e86c9853ef1db680df4317d0f3  PROVENANCE.json
```

Commands:

```sh
cmp MANIFEST.yaml PRIOR_BUILD/MANIFEST.yaml
cmp PROVENANCE.json PRIOR_BUILD/PROVENANCE.json
```

Observed result: exit 0 with no stdout for both comparisons. The verifier checks the files'
canonical JSON hashes and confirms that status remains `GENERATED`, labels remain exactly
`["GENERATED", "PARTIAL"]`, and `productionized` remains false.

Command:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import os; prior=[]
for parent, dirs, files in os.walk("PRIOR_BUILD"):
 dirs.sort(); files.sort(); prior.extend(os.path.relpath(os.path.join(parent,name),"PRIOR_BUILD") for name in files)
missing=[path for path in prior if not os.path.isfile(path)]; assert not missing, missing
roots={name:("directory" if os.path.isdir(os.path.join("PRIOR_BUILD",name)) else "file" if os.path.isfile(os.path.join("PRIOR_BUILD",name)) else "other") for name in sorted(os.listdir("PRIOR_BUILD"))}
observed={name:("directory" if os.path.isdir(name) else "file" if os.path.isfile(name) else "other") for name in roots}; assert roots==observed,(roots,observed)
print("prior_regular_paths_preserved: PASS ({} of {})".format(len(prior),len(prior))); print("prior_top_level_kinds_preserved: PASS ({} of {})".format(len(roots),len(roots)))'
```

Observed result: exit 0:

```text
prior_regular_paths_preserved: PASS (54 of 54)
prior_top_level_kinds_preserved: PASS (17 of 17)
```

Command:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import os,sys;sys.path.insert(0,"environment");import learner_view; inventory=learner_view.source_inventory("."); selected=sorted(path for path in inventory if path.startswith("environment")); print("learner_environment_selection:"); print(chr(10).join(selected)); forbidden=["LICENSE","ARTIFACT_INVENTORY.sha256"]; present=[path for path in forbidden if os.path.lexists(path)]; assert not present,present; print("policy_specific_roots_absent: PASS")'
```

Observed result: exit 0:

```text
learner_environment_selection:
environment
environment/README.md
environment/learner_view.py
policy_specific_roots_absent: PASS
```

No local inventory root was created.

## Bounded network-suite attempts

Commands:

```sh
/usr/bin/timeout 15s /arm/tools/nodejs/node/22.21.0/linux64/bin/node \
  --test public_tests/*.test.js
SUBMISSION_ROOT=sealed/reference /usr/bin/timeout 15s \
  /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test public_tests/*.test.js
/usr/bin/timeout 15s /arm/tools/nodejs/node/22.21.0/linux64/bin/node \
  --test sealed/reference_tests/*.test.js
```

Observed result: exit 1 for all three commands. Each public command reported the
`public_tests/framework.test.js` file group failed with `ERR_TEST_FAILURE` (0 groups passed, 1
failed). The sealed command reported 3 JavaScript file groups: `regressions.test.js` passed while
`abort-socket.test.js` and `reference.test.js` failed (1 passed, 2 failed).

The following bounded direct command exposed the host restriction:

```sh
/usr/bin/timeout 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node \
  sealed/reference_tests/abort-socket.test.js
```

Observed result: exit 1 at the first test before a connection was created:

```text
error: 'listen EPERM: operation not permitted 127.0.0.1'
code: 'EPERM'
```

The file-group failures do not establish an implementation failure or success. This sandbox still
prohibits ephemeral loopback listeners, so full HTTP integration, `app.listen`, real-socket abort
handling, and benchmark behavior remain inconclusive and require a network-capable independent
validator.

## Claims and limitations

- The pack remains `GENERATED` + `PARTIAL`; it does not claim `BUILDS`, `TESTED`, `FUZZED`,
  `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.
- No learner view was materialized or transferred. In-place inventory and unit checks do not
  establish transfer verification.
- No benchmark, fuzz run, load result, profiler result, cross-version result, or production-readiness
  assessment was produced.
- The linked `NOASSERTION`-licensed tutorial was not fetched or inspected. No upstream originality,
  licensing, or availability claim is added.
- The factory, not this record, supplies and validates the content-addressed artifact inventory.
