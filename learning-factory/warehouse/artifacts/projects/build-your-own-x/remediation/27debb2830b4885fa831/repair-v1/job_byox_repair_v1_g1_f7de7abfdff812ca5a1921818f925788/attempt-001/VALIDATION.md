# Validation record

Artifact status remains `GENERATED` + `PARTIAL`; independent validation is still `REQUIRED`, and
`productionized` remains `false`. This repair-generation record was created on 2026-08-31 in the
allocated production workspace. Commands ran from the challenge root unless another working
directory is shown, with bounded timeouts where execution was possible. Repeated shell-wrapper
user/group lookup warnings are environmental noise and are omitted below.

## Runtime inventory

```sh
for tool in node npm nodejs deno bun qjs js quickjs jjs d8 gjs; do
  if command -v "$tool" >/dev/null 2>&1; then command -v "$tool"; else echo "$tool: NOT FOUND"; fi
done
python3 --version
gjs --version
```

Exit status 0. Observed:

```text
node: NOT FOUND
npm: NOT FOUND
nodejs: NOT FOUND
deno: NOT FOUND
bun: NOT FOUND
qjs: NOT FOUND
js: NOT FOUND
quickjs: NOT FOUND
jjs: NOT FOUND
d8: NOT FOUND
/usr/bin/gjs
Python 3.6.8
gjs 1.56.2
```

No dependency installation or network access was attempted.

## Deterministic artifact checks

```sh
timeout 30s python3 -B environment/verify_artifact.py
```

Exit status 0. Observed:

```text
artifact verification: PASS (23 required paths, 0 forbidden paths)
JSON and credential-pattern scans: PASS
explicit ECMAScript module scopes: PASS (29 import-bearing .js files)
learner source isolation/host-API scan: PASS (10 files)
learner-view allowlist policy: PASS (25 files; 0 sealed hash collisions)
lightweight JavaScript delimiter scan: PASS (31 files; not a syntax check)
```

This candidate-supplied checker verifies required regular files, forbidden-path absence, the exact
manifest object, provenance bindings, JSON readability, credential patterns, explicit module scope
for import-bearing `.js`, learner-source import/host-API boundaries, the learner-view policy, and a
delimiter scan. It is deterministic structural/static evidence, not independent validation, a full
secret audit, or an ECMAScript parser.

The progressive-disclosure policy received its separate no-output check:

```sh
timeout 30s python3 -B environment/learner_view.py check-policy
```

Exit status 0:

```json
{"excluded_artifact_files": 42, "learner_files": 25, "sealed_content_hash_collisions": 0}
```

Only `check-policy` ran. The worker did not invoke `export` or `verify`, did not create a learner
workspace, and makes no transfer-validation claim. Those operations are reserved for a trusted
worker harness with an external destination.

Artifact inventory commands:

```sh
find AGENTS.md CONCEPTS.md DESIGN_QUESTIONS.md LICENSE_BOUNDARY.md MANIFEST.yaml \
  PROVENANCE.json README.md REQUIREMENTS.md VALIDATION.md starter public_tests environment \
  sealed adversarial debugging review_exercises benchmarks -type f | wc -l
find starter public_tests environment sealed adversarial debugging review_exercises benchmarks \
  -type d | wc -l
find AGENTS.md CONCEPTS.md DESIGN_QUESTIONS.md LICENSE_BOUNDARY.md MANIFEST.yaml \
  PROVENANCE.json README.md REQUIREMENTS.md VALIDATION.md starter public_tests environment \
  sealed adversarial debugging review_exercises benchmarks -type l | wc -l
find AGENTS.md CONCEPTS.md DESIGN_QUESTIONS.md LICENSE_BOUNDARY.md MANIFEST.yaml \
  PROVENANCE.json README.md REQUIREMENTS.md VALIDATION.md starter public_tests environment \
  sealed adversarial debugging review_exercises benchmarks ! -type f ! -type d ! -type l \
  -print | wc -l
```

Each exited 0; outputs in order were 67 regular files, 23 directories below the artifact root, zero
symlinks, and zero special entries.

The prior pack's safe top-level names and entry kinds were checked after copying:

```sh
for path in PRIOR_BUILD/*; do
  name=${path#PRIOR_BUILD/}
  test -e "$name" || { echo "missing: $name"; exit 1; }
  if test -d "$path"; then test -d "$name" || exit 1; else test -f "$name" || exit 1; fi
done
```

It exited 0 with no output. Content differences are the documented repairs; no prior top-level entry
was omitted or changed from a file to a directory (or conversely).

The immutable contract files remain byte-identical to the archived prior copies:

```sh
cmp -s PROVENANCE.json PRIOR_BUILD/PROVENANCE.json
cmp -s MANIFEST.yaml PRIOR_BUILD/MANIFEST.yaml
sha256sum PROVENANCE.json MANIFEST.yaml
```

Both `cmp` commands exited 0. `sha256sum` exited 0 with:

```text
38d103ccd74dbebc95e4170aa8f166278e1394ee3f7dc7fcb6a961457bd6b8ee  PROVENANCE.json
008027c09f7371397b2b4061577c52df3d6a5dbe83a31caded2bd86304fbaf33  MANIFEST.yaml
```

## Supplemental transformed execution

```sh
set -o pipefail
timeout 30s python3 -B sealed/reference_tests/gjs_bundle.py | timeout 30s gjs /dev/stdin
```

Exit status 0. Standard output:

```text
GJS_TRANSPILED_SMOKE_PASS
```

GJS also emitted `JS WARNING: [/dev/stdin 5]: reference to undefined property "line"` while a
deliberately locationless error path was exercised. The assertion-bearing smoke covered ordinary
tree/VM behavior plus the repair counterexamples: inherited object-name identifiers, grouped
assignment, a 1,001-term flat addition, the documented engine-local two-step boundary, and rejection
of a custom code-array prototype without invoking its inherited `at` getter. The helper mechanically
removes ESM syntax and downlevels modern expressions, so this is supplemental algorithm evidence
only. It does not validate original-module syntax/linkage or execute any `node:test` file and earns
no validation label.

## Original test and benchmark attempts

The documented entry points were attempted with 30-second bounds:

```sh
(cd starter && timeout 30s npm test)
(cd starter && timeout 30s npm run test:public)
(cd sealed/reference && timeout 30s npm test)
timeout 30s node --test debugging/precedence/buggy-parser.test.js
timeout 30s node benchmarks/run.mjs
```

Every command exited 127. The three npm attempts each reported
`timeout: failed to run command ‘npm’: No such file or directory`; the other two reported the same
message for `node`. No original JavaScript module, test assertion, or benchmark workload ran.

An optional Python ECMAScript-parser probe was also bounded:

```sh
timeout 30s python3 -B -c 'import esprima; print(esprima.__version__)'
```

It exited 1 with `ModuleNotFoundError: No module named 'esprima'`. Therefore the record makes no
original ECMAScript syntax claim.

## Not performed

No learner-view export, independent Node-version test, fuzzing, coverage or mutation analysis,
benchmark measurement, profiling, transfer validation, upstream comparison, security audit,
production deployment, or bit-for-bit generator replay was performed. The benchmark contains no
fabricated measurements. Fresh independent review remains mandatory.
