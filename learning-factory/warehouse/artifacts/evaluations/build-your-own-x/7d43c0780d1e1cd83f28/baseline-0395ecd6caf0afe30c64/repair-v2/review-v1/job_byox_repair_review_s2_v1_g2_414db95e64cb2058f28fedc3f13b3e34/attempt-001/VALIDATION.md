# Independent validation record

Review date: 2026-09-02  
Scope: immutable `CANDIDATE/` submitted by builder job
`job_byox_repair_s2_v1_g2_9e8c5be9ccc9e665cada2943439a5777`.

Commands were run from the review workspace root unless a `cd CANDIDATE` prefix is shown. All
potentially waiting commands were bounded. Repeated `/usr/bin/id` warnings about unmapped numeric
user/group IDs were emitted by the command wrapper and did not change command exit codes.

## Toolchains

```sh
/arm/tools/nodejs/node/22.21.0/linux64/bin/node --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed: both exited 0.

```text
v22.21.0
Python 3.11.5
```

Node.js and Python were the only configured toolchains relevant to this dependency-free
CommonJS/Python artifact. The configured C/C++, assembly, Java, Go, QEMU, GLib, Flex, and Bison
roots were out of scope and were not invoked; no relevant configured toolchain was unavailable.

## Submission integrity and structure

The following deterministic command was run before and after review:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import hashlib,os; root="CANDIDATE"; paths=sorted(os.path.relpath(os.path.join(parent,name),root).replace(os.sep,"/") for parent,dirs,files in os.walk(root) for name in files); digest=hashlib.sha256(); [(digest.update(path.encode("utf-8")+b"\0"),digest.update(open(os.path.join(root,*path.split("/")),"rb").read())) for path in paths]; print("files",len(paths)); print("aggregate_sha256",digest.hexdigest())'
```

Observed before and after, exit 0:

```text
files 54
aggregate_sha256 a5a9c85e0bc68023d18148089ce41f3d19f80cec256eccec1af62e6ebd49e761
```

```sh
find CANDIDATE -type f -printf '%m %p\n' | sort | uniq -c
find CANDIDATE -mindepth 1 ! -type f ! -type d -print
```

Observed: all 54 submitted files had mode `0444`; the special-entry query printed nothing. No
submitted byte was changed. A reviewer-owned scratch projection was deleted after its checks.

The builder verifier was executed only as corroboration, not accepted as proof:

```sh
cd CANDIDATE
/usr/bin/timeout 10s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/verify_artifact.py
```

Observed: exit 0.

```text
required_paths: PASS (24/24)
forbidden_paths: PASS (0 present)
file_types: PASS (54 regular files, 18 directories, 0 special entries)
learner_projection: PASS (20 regular files, 4 directories, 0 evaluator roots selected)
metadata_values: PASS (manifest and provenance canonical hashes)
credential_scan: PASS (54 regular files scanned)
```

Independent enumeration, metadata checks, projection checks, and credential-pattern scanning below
cross-check the material parts of this output.

## Syntax

```sh
cd CANDIDATE
/usr/bin/timeout 20s /bin/bash -c 'javascript_count=0; while IFS= read -r javascript_source; do /arm/tools/nodejs/node/22.21.0/linux64/bin/node --check "$javascript_source" || exit 1; javascript_count=$((javascript_count + 1)); done < <(find starter public_tests sealed benchmarks debugging review_exercises -type f -name "*.js" -print | sort); echo "javascript_syntax: PASS ($javascript_count files)"'
```

Observed: exit 0, `javascript_syntax: PASS (22 files)`.

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import os; paths=sorted(os.path.join(p,n) for p,d,fs in os.walk("CANDIDATE") for n in fs if n.endswith(".py")); [compile(open(path,encoding="utf-8").read(),path,"exec") for path in paths]; print("python_syntax: PASS ({} files)".format(len(paths)))'
```

Observed: exit 0, `python_syntax: PASS (3 files)`.

## Executable test evidence

### Socket-free regression suite

```sh
cd CANDIDATE
/usr/bin/timeout 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/regressions.test.js
```

Observed: exit 0; TAP reported 9 tests, 9 passed, 0 failed. The cases covered supported-method
fallthrough, gated request isolation, pre-fired abort/destruction/error, invalid UTF-8,
post-attachment destruction, content-coding lists, bodyless entity/framing headers, and native
error framing.

### Targeted reference and public subsets

```sh
cd CANDIDATE
/usr/bin/timeout 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test-name-pattern='^(compose|compiled patterns|middleware prefixes|JSON middleware reports synthetic)' sealed/reference_tests/reference.test.js
/usr/bin/timeout 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test-name-pattern='^exports the documented' public_tests/framework.test.js
/usr/bin/timeout 10s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -m unittest sealed/reference_tests/test_learner_view.py -v
```

Observed: all exited 0. TAP reported 4/4 targeted reference tests and 1/1 public API test passed;
unittest reported 3/3 learner-view tests passed.

### Documented repair probes

The four exact `node -e` commands printed in `CANDIDATE/VALIDATION.md:110-156` were independently
rerun with `/usr/bin/timeout 3s` and the configured Node executable. All exited 0:

```text
destroy_before_end: PASS rejected:BODY_ABORTED
native_error_framing: PASS sanitized
bodyless_entity_headers: PASS {}
identity_encoding_list: PASS
```

This reproduces the observations; the builder's embedded scripts were not treated as proof by
themselves.

### Reviewer-authored socket-free probes

Reviewer-authored probes used the configured Node executable with inline `node -e` assertions
against `./sealed/reference`.

One compact form of the reviewer contract probe was retained verbatim and rerun:

```sh
cd CANDIDATE
/usr/bin/timeout 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node -e 'const a=require("node:assert/strict"),{PassThrough}=require("node:stream"),tiny=require("./sealed/reference");class R{constructor(){this.statusCode=200;this.h=new Map;this.headersSent=this.writableEnded=this.destroyed=false;this.body=Buffer.alloc(0)}setHeader(n,v){this.h.set(n.toLowerCase(),v)}getHeader(n){return this.h.get(n.toLowerCase())}hasHeader(n){return this.h.has(n.toLowerCase())}removeHeader(n){this.h.delete(n.toLowerCase())}end(v){this.body=v===undefined?Buffer.alloc(0):Buffer.from(v);this.headersSent=this.writableEnded=true}destroy(e){this.destroyed=true;this.error=e}}async function d(app,m,u){const q={method:m,url:u,headers:{}},r=new R;await app(q,r);return r}(async()=>{const app=tiny();app.get("/word",(q,r)=>r.send("café"));app.get("/known",(q,r)=>r.send("yes"));app.get("/boom",()=>{throw Error("private")});let r=await d(app,"HEAD","/word");a.equal(r.body.length,0);a.equal(r.getHeader("content-length"),"5");r=await d(app,"PUT","/known");a.equal(r.statusCode,405);a.equal(r.getHeader("allow"),"GET, HEAD, OPTIONS");r=await d(app,"GET","/boom");a.equal(r.statusCode,500);a.match(r.body.toString(),/Internal Server Error/);a.doesNotMatch(r.body.toString(),/private/);const q=new PassThrough;q.headers={"content-type":"application/problem+json","content-encoding":"identity, identity"};q.complete=true;let n=0;const p=tiny.json({limit:8})(q,{},()=>{n++});q.end("42");await p;a.equal(q.body,42);a.equal(n,1);for(const e of ["data","end","aborted","error","close"])a.equal(q.listenerCount(e),0);console.log("reviewer_compact_contract: PASS")})().catch(e=>{console.error(e);process.exitCode=1})'
```

Observed: exit 0, `reviewer_compact_contract: PASS`.

Four larger inline probe programs were also executed ephemerally with the same timeout and Node
path. Their assertion coverage and exact observed result lines are recorded below; their full source
was not added to the submitted or review artifacts.

The first serialized native GET and HEAD error responses and asserted status, byte-accurate
`Content-Length`, absent HEAD payload, hidden internal error text, and a visible generic 500
message. The second used an independent in-memory response double to assert registration chaining,
mount boundaries, named and wildcard captures, duplicate query values, fixed-target request state,
deterministic Allow sets, automatic OPTIONS, supported-method 404, UTF-8 HEAD length, explicit HEAD
precedence, malformed path 400, hidden 500 text, post-header destruction, and 204 cleanup. The
third covered scalar/array/empty/pre-ended JSON, `+json`, identity lists, non-JSON pass-through,
length mismatch, malformed length/coding, unsupported coding, streamed limits, invalid UTF-8, and
listener cleanup. The fourth serialized native 199/204/304 responses with and without keep-alive
and rejected every defined entity/framing header and payload byte.

Observed: all four commands exited 0.

```text
native_head_and_error_boundary: PASS
reviewer_socket_free_contract: PASS (routing, request state, response, error boundary)
reviewer_json_matrix: PASS
native_bodyless_framing_matrix: PASS
```

The inline source was reviewer-owned ephemeral test input and was not added to `CANDIDATE/`.

## Bounded network-suite attempts

```sh
cd CANDIDATE
/usr/bin/timeout 15s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test public_tests/framework.test.js
SUBMISSION_ROOT=sealed/reference /usr/bin/timeout 15s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test public_tests/framework.test.js
/usr/bin/timeout 15s /arm/tools/nodejs/node/22.21.0/linux64/bin/node --test sealed/reference_tests/abort-socket.test.js sealed/reference_tests/reference.test.js sealed/reference_tests/regressions.test.js
/usr/bin/timeout 10s /arm/tools/nodejs/node/22.21.0/linux64/bin/node sealed/reference_tests/abort-socket.test.js
```

Observed: all exited 1. Each public command reported its file group failed with
`ERR_TEST_FAILURE`. The sealed command reported 1/3 file groups passed: the socket-free regression
group passed, while the abort-socket and reference groups failed. Running the abort suite directly
showed the cause at its first operation, before any connection was created:

```text
error: 'listen EPERM: operation not permitted 127.0.0.1'
code: 'EPERM'
```

Running `reference.test.js` directly reported 4 socket-free tests passed and 11 listener-dependent
tests failed with the same `listen EPERM`. These outcomes establish a host restriction, not success
or failure of the unexecuted HTTP assertions.

## Learner projection

A reviewer-owned destination outside `CANDIDATE/` was created, then removed after checking:

```sh
mkdir REVIEW_TMP
/usr/bin/timeout 10s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B CANDIDATE/environment/learner_view.py project --source CANDIDATE --destination REVIEW_TMP/learner-view
/usr/bin/timeout 10s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B CANDIDATE/environment/learner_view.py verify --source CANDIDATE --view REVIEW_TMP/learner-view
find REVIEW_TMP/learner-view -mindepth 1 -printf '%y %P\n' | sort
```

Observed: projection and verification exited 0 and each reported 20 regular files, 4 directories,
and 0 other entries. Independent inventory contained only:

```text
README.md, AGENTS.md, MANIFEST.yaml, REQUIREMENTS.md, CONCEPTS.md, DESIGN_QUESTIONS.md
starter/ (9 files plus 2 directories)
public_tests/ (3 files plus 1 directory)
environment/README.md
environment/learner_view.py
```

An independent presence probe found none of `sealed`, `adversarial`, `debugging`,
`review_exercises`, `benchmarks`, `PROVENANCE.json`, `LICENSE_BOUNDARY.md`, `VALIDATION.md`, or
`environment/verify_artifact.py`.

Negative cases:

```sh
mkdir REVIEW_TMP/learner-view/sealed
/usr/bin/timeout 10s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B CANDIDATE/environment/learner_view.py verify --source CANDIDATE --view REVIEW_TMP/learner-view
rmdir REVIEW_TMP/learner-view/sealed
/usr/bin/timeout 10s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B CANDIDATE/environment/learner_view.py project --source CANDIDATE --destination REVIEW_TMP/learner-view
/usr/bin/timeout 10s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B CANDIDATE/environment/learner_view.py project --source CANDIDATE --destination CANDIDATE/reviewer-overlap-probe
```

Observed: the three Python commands exited 1 as expected, respectively reporting
`extra=sealed`, `destination must not already exist`, and `source and destination must not overlap`.
No overlap destination was created. The scratch tree was subsequently removed and its absence was
confirmed.

## Metadata, provenance, dependencies, and credentials

```sh
cd CANDIDATE
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -c 'import json; m=json.load(open("MANIFEST.yaml")); p=json.load(open("PROVENANCE.json")); checks={"project_id":m["project_id"]==p["project"]["project_id"],"source_id":m["source_id"]==p["source"]["source_id"]==p["project"]["source_id"],"source_commit":m["source_commit"]==p["source"]["commit_hash"]==p["project"]["metadata"]["provenance"]["source_commit"],"snapshot_link":m["provenance_sha256"]==p["snapshot_sha256"],"labels":m["validation_labels"]==["GENERATED","PARTIAL"] and m["status"]=="GENERATED" and m["productionized"] is False}; print(checks); assert all(checks.values())'
sha256sum MANIFEST.yaml PROVENANCE.json
```

Observed: exit 0; all five cross-link/status checks were `True`.

```text
604aa5df5e7dd82067bb8591aa638955360bc2bc363b0b8e06455e422a203fe4  MANIFEST.yaml
0b89a7a1874b0b75c4f6835446a0ed19d24a90e86c9853ef1db680df4317d0f3  PROVENANCE.json
```

Independent canonical JSON hashes were:

```text
MANIFEST.yaml e2299a901563deda64a2679fbf65a36440bfbbc54206f834f3ce438dec98aab3
PROVENANCE.json 8830de4919fec4723ad5ea1219617b2d1c75a922aa1f3fe0e02152c6e90d9e1d
```

Static `require(...)` inspection found only Node built-ins and local files in the starter/reference
and their tests; both package documents have no dependency sections. No shell execution, dynamic
evaluation, or process-global request slot was found in the reference. The intentionally broken
review exercise's module-global variable is outside the learner projection and clearly labeled.

An independent Python byte-pattern scan checked all 54 files for PEM private-key headers, AWS key
IDs, GitHub tokens, OpenAI-style keys, and quoted password/API-key/client-secret/access-token
assignments. It exited 0 with `hits []`. This is a bounded heuristic, not proof of secret absence.

`find . -maxdepth 2 -name PRIOR_BUILD -print` printed nothing. Network access and the source baseline
were unavailable, so the linked tutorial, originality statement, source commit, catalog license
evidence, and source-derived hashes were not externally authenticated.

## Claim review

The manifest says `GENERATED` + `PARTIAL`, requires independent validation, and sets
`productionized` to false. The builder record explicitly disclaims `BUILDS`, `TESTED`, `FUZZED`,
`BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, and `PRODUCTIONIZED`. The record accurately calls
its own scripts and prose builder observations. This advisory `PASS` does not modify the manifest or
promote a label.
