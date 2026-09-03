# Independent validation record

Review date: 2026-09-02  
Candidate policy: CANDIDATE/ was treated as immutable.  
Default command directory: CANDIDATE/  
Verdict informed by these observations: REVISE

Commands were bounded where they could wait. A builder-authored script was inspected before being
run and is reported only as one independently reproduced observation, not as acceptance proof.

## Toolchains

Command:

    /arm/tools/nodejs/node/22.21.0/linux64/bin/node --version

Observed: exit 0, stdout v22.21.0.

Command:

    /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version

Observed: exit 0, stdout Python 3.11.5.

These were the only relevant configured toolchains for this dependency-free CommonJS/Python
validation tooling. No required language toolchain was unavailable. The configured Java, GCC,
binutils, Arm, QEMU, Go, NASM, GLib, Flex, and Bison roots were not invoked because the candidate
does not use them; their availability is not asserted.

## Static structure and metadata

JavaScript syntax command:

    javascript_count=0
    while IFS= read -r javascript_source; do
      /arm/tools/nodejs/node/22.21.0/linux64/bin/node --check "$javascript_source" || exit 1
      javascript_count=$((javascript_count + 1))
    done < <(find starter public_tests sealed benchmarks debugging review_exercises -type f -name '*.js' -print | sort)
    printf 'javascript_syntax: PASS (%s files)\n' "$javascript_count"

Observed: exit 0.

    javascript_syntax: PASS (22 files)

Artifact verifier command:

    /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/verify_artifact.py

Observed: exit 0.

    required_paths: PASS (24/24)
    forbidden_paths: PASS (0 present)
    file_types: PASS (54 regular files, 18 directories, 0 special entries)
    learner_projection: PASS (21 regular files, 4 directories, 0 evaluator roots selected)
    metadata_values: PASS (manifest and provenance canonical hashes)
    credential_scan: PASS (54 regular files scanned)

This result proves only the inspected script's stated checks. It is not a hidden-secret audit or an
orchestrator inventory.

Raw and canonical metadata hash command:

    sha256sum MANIFEST.yaml PROVENANCE.json && /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import hashlib,json; [(lambda b,p: print(p, hashlib.sha256(b).hexdigest()))(json.dumps(json.load(open(p,encoding="utf-8")),sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8"),p) for p in ("MANIFEST.yaml","PROVENANCE.json")]'

Observed: exit 0.

    604aa5df5e7dd82067bb8591aa638955360bc2bc363b0b8e06455e422a203fe4  MANIFEST.yaml
    0b89a7a1874b0b75c4f6835446a0ed19d24a90e86c9853ef1db680df4317d0f3  PROVENANCE.json
    MANIFEST.yaml e2299a901563deda64a2679fbf65a36440bfbbc54206f834f3ce438dec98aab3
    PROVENANCE.json 8830de4919fec4723ad5ea1219617b2d1c75a922aa1f3fe0e02152c6e90d9e1d

Identifier-coherence command:

    /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import json; m=json.load(open("MANIFEST.yaml")); p=json.load(open("PROVENANCE.json")); checks={"project_id":m["project_id"]==p["project"]["project_id"],"source_id":m["source_id"]==p["source"]["source_id"]==p["project"]["source_id"],"source_commit":m["source_commit"]==p["source"]["commit_hash"]==p["project"]["metadata"]["provenance"]["source_commit"],"snapshot_link":m["provenance_sha256"]==p["snapshot_sha256"]}; print(checks); assert all(checks.values())'

Observed: exit 0.

    {'project_id': True, 'source_id': True, 'source_commit': True, 'snapshot_link': True}

JSON parse command:

    /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import json; paths=["MANIFEST.yaml","PROVENANCE.json","starter/package.json","sealed/reference/package.json"]; [json.load(open(path,encoding="utf-8")) for path in paths]; print("json_parse: PASS (4 files)")'

Observed: exit 0.

    json_parse: PASS (4 files)

Learner selection command:

    /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import sys;sys.path.insert(0,"environment");import learner_view; inventory=learner_view.source_inventory("."); print("\n".join(sorted(inventory)))'

Observed: exit 0. It selected 21 files and four directories. The selected environment entries were:

    environment
    environment/README.md
    environment/learner_view.py
    environment/verify_artifact.py

No symlinks, executable files, or files lacking world-read permission were found by:

    find . -type l -print
    find . -type f ! -perm -004 -print
    find . -type f -perm /111 -print | sort

Observed: exit 0 with no output.

## Socket-free behavioral checks

Regression command:

    /usr/bin/timeout 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/regressions.test.js

Observed: exit 0; TAP reported 5 tests, 5 passed, 0 failed.

Filtered reference command:

    /usr/bin/timeout 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test-name-pattern='^(compose|compiled patterns|middleware prefixes|JSON middleware reports synthetic)' sealed/reference_tests/reference.test.js

Observed: exit 0; TAP reported 4 tests, 4 passed, 0 failed.

Learner-view unit command:

    /usr/bin/timeout 10s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -m unittest sealed/reference_tests/test_learner_view.py -v

Observed: exit 0; 3 tests ran and all passed.

Socket-free public API command:

    /usr/bin/timeout 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test-name-pattern='^exports the documented' public_tests/framework.test.js

Observed: exit 0; TAP reported 1 test, 1 passed, 0 failed.

## Network-bearing attempts

Reference public-suite command:

    SUBMISSION_ROOT=sealed/reference /usr/bin/timeout 15s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test public_tests/framework.test.js

Observed: exit 1. Node reported the framework.test.js file group failed with ERR_TEST_FAILURE; no
test group passed.

Raw-socket diagnostic command:

    /usr/bin/timeout 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/abort-socket.test.js

Observed: exit 1. The first and only test failed before a socket connection:

    error: 'listen EPERM: operation not permitted 127.0.0.1'
    code: 'EPERM'

This independently confirms an environment limitation, not a candidate behavioral failure.

## Independent adversarial checks

### Destruction before readable end

Command:

    /usr/bin/timeout 2s /arm/tools/nodejs/node/22.21.0/linux64/bin/node -e 'const {PassThrough}=require("node:stream");const tiny=require("./sealed/reference");const req=new PassThrough();req.headers={"content-type":"application/json"};req.complete=true;const parsing=tiny.json({limit:8})(req,{},()=>{});req.destroy();Promise.race([parsing.then(()=>"resolved",e=>"rejected:"+e.code),new Promise(r=>setTimeout(()=>r("pending"),100))]).then(outcome=>{const ok=outcome==="rejected:BODY_ABORTED";console.log("destroy_before_end:",ok?"PASS":"FAIL",outcome);process.exitCode=ok?0:1;});'

Observed: exit 1.

    destroy_before_end: FAIL pending

The middleware did not satisfy R6's required 400 settlement.

### Native error-response framing

Command:

    /arm/tools/nodejs/node/22.21.0/linux64/bin/node -e 'const http=require("node:http"),{Duplex}=require("node:stream"),{sendError}=require("./sealed/reference/src/application");let raw="";const socket=new Duplex({read(){},write(c,e,cb){raw+=c;cb()}});const res=new http.ServerResponse({method:"GET",httpVersionMajor:1,httpVersionMinor:1,shouldKeepAlive:false});res.assignSocket(socket);res.setHeader("transfer-encoding","chunked");res.setHeader("content-encoding","gzip");res.on("finish",()=>{const bad=/transfer-encoding: chunked/i.test(raw)&&/content-length: 58/i.test(raw)&&/content-encoding: gzip/i.test(raw);console.log("native_error_framing:",bad?"FAIL":"PASS",bad?"TE+CL and stale gzip emitted":"sanitized");process.exitCode=bad?1:0});sendError(res,Error("boom"));'

Observed: exit 1.

    native_error_framing: FAIL TE+CL and stale gzip emitted

This used Node's real ServerResponse serializer over an in-memory Duplex; it did not require a
listener.

### Entity headers on a body-forbidden status

Command:

    /arm/tools/nodejs/node/22.21.0/linux64/bin/node -e 'const {decorateResponse}=require("./sealed/reference/src/response");class R{constructor(){this.statusCode=200;this.headers=new Map;this.writableEnded=this.destroyed=false}setHeader(n,v){this.headers.set(n.toLowerCase(),String(v))}getHeader(n){return this.headers.get(n.toLowerCase())}hasHeader(n){return this.headers.has(n.toLowerCase())}removeHeader(n){this.headers.delete(n.toLowerCase())}end(){this.writableEnded=true}}const res=new R;decorateResponse(res,"GET");res.set("content-encoding","gzip").status(204).send("x");const bad=res.hasHeader("content-encoding");console.log("bodyless_entity_headers:",bad?"FAIL":"PASS",JSON.stringify(Object.fromEntries(res.headers)));process.exitCode=bad?1:0;'

Observed: exit 1.

    bodyless_entity_headers: FAIL {"content-encoding":"gzip"}

### Identity Content-Encoding list

Command:

    /arm/tools/nodejs/node/22.21.0/linux64/bin/node -e 'const {PassThrough}=require("node:stream");const tiny=require("./sealed/reference");const req=new PassThrough;req.headers={"content-type":"application/json","content-encoding":"identity, identity"};req.complete=true;const parsing=tiny.json({limit:8})(req,{},()=>{});req.end("{}");parsing.then(()=>console.log("identity_encoding_list: PASS"),e=>{console.log("identity_encoding_list: FAIL",e.status,e.code);process.exitCode=1});'

Observed: exit 1.

    identity_encoding_list: FAIL 415 UNSUPPORTED_CONTENT_ENCODING

## Limitations and non-claims

- Loopback listen is unavailable, so public/reference HTTP integration, real-socket abort, and
  app.listen behavior are inconclusive.
- No benchmark or fuzz harness was run. No performance, security, production, or cross-version
  conclusion is made.
- No learner view was created or transferred. In-place selection and comparison tests do not
  establish TRANSFER_VERIFIED.
- The catalog baseline, linked upstream repository, and external content-addressed inventory were
  unavailable. Provenance fields were checked for internal coherence only; originality and linked
  licensing were not independently verified.
- PRIOR_BUILD is absent from this review workspace, so the builder's reported 50-of-50 preservation
  check could not be repeated.
- Nothing here promotes or edits CANDIDATE/MANIFEST.yaml. Only an orchestrator-captured acceptance
  validator can publish REVIEWED.
