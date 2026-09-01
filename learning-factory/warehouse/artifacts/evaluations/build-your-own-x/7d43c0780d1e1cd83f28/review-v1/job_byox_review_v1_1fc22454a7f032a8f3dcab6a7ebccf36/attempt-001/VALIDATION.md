# Independent validation record

Review date: 2026-08-31. Commands were run from `CANDIDATE/` unless stated
otherwise. The submitted directory was treated as immutable. Login-shell
startup also printed unrelated UID/GID name-lookup warnings; those warnings are
omitted below.

## Toolchain discovery

```bash
for tool in node npm nodejs bun deno qjs js docker podman apptainer singularity; do
  command -v "$tool" || true
done
python3 --version
```

Observed: every JavaScript runtime and container command produced no path.
Python reported `Python 3.6.8`.

```text
$ node --version
/bin/bash: node: command not found
exit 127
```

No module-loader command was available, and a bounded search of `/usr/bin` and
`/usr/local/bin` found only `/usr/bin/nodeset`, which is not a JavaScript
runtime.

## Structural and metadata checks

```text
$ python3 environment/verify-structure.py
PASS required paths: 23 regular files
PASS forbidden paths: 21 absent
PASS artifact node types: 62 files, 25 directories
PASS immutable metadata: strict JSON and expected SHA-256
exit 0
```

This is a builder-controlled verifier, so its output proves only the checks
implemented in that script. I separately inventoried all candidate files,
checked node types, and recomputed the published digests.

```bash
python3 -m json.tool MANIFEST.yaml >/dev/null
python3 -m json.tool PROVENANCE.json >/dev/null
python3 -m json.tool starter/package.json >/dev/null
python3 -m json.tool sealed/reference/package.json >/dev/null
```

Observed: all four commands exited 0.

```text
$ sha256sum MANIFEST.yaml PROVENANCE.json starter/package.json sealed/reference/package.json
a4529eb3613733b2930841b447d4495d38f6945c54363fb61cee0132207c8dbd  MANIFEST.yaml
dc328469b4988520ffa7a9d9f58e207914721720b1a6d93bac854dcad0796f05  PROVENANCE.json
7c9146726d251329f5828e93d4ba00dfb438c626f042edaf3441eecc9dd98650  starter/package.json
d72d3b5a395ae904abe5992346651a93e1b1b99289ddcc1ecf85a85c5aebd6a3  sealed/reference/package.json
exit 0
```

These values exactly reproduce `CANDIDATE/VALIDATION.md`.

Test declarations were counted without treating them as results:

```bash
awk '/^[[:space:]]*test\(/ {count += 1} END {print count + 0}' public_tests/*.test.js
awk '/^[[:space:]]*test\(/ {count += 1} END {print count + 0}' sealed/reference_tests/*.test.js
```

Observed output was `21` and `33`, respectively.

## JavaScript checks attempted

```text
$ node --test public_tests/*.test.js
/bin/bash: node: command not found
exit 127

$ node --test sealed/reference_tests/*.test.js
/bin/bash: node: command not found
exit 127

$ node adversarial/run.js
/bin/bash: node: command not found
exit 127

$ node benchmarks/router-benchmark.js
/bin/bash: node: command not found
exit 127
```

Consequently there are no observed build, test, adversarial, exercise, or
benchmark successes and no benchmark measurements. Syntax validity and runtime
behavior are inconclusive on this host.

## Static correctness review

The reference and all harness/test sources were read with numbered lines. A
specific dispatch defect was traced as follows:

1. `sealed/reference/src/index.js:104` decodes every captured value and can
   throw `URIError`.
2. Lines 417-425 catch that error while matching a layer, assign it to
   `errorState`, and continue without adding the shared registration to
   `paramsByRegistration`.
3. If the next handler in that registration has arity four, lines 417-422 call
   the same matcher again; it throws again, so the handler is never invoked.
4. Lines 471-473 then exhaust to the default 500 unless a later middleware
   error handler is present.

This conflicts with `REQUIREMENTS.md:69-75,136-139` for a route registration
that contains a normal handler followed by an error handler. The supplied tests
cover malformed captures followed by global `use` error middleware, but no
route-local malformed-capture handler was found. This is static evidence, not a
reported test execution.

The public helper's deadline is a `setTimeout` in the same process as the HTTP
server (`public_tests/_helpers.js:59-63`); the sealed helper and adversarial
harness use the same model. A synchronously non-returning target blocks that
event loop, so the “absolute”/“fails boundedly” wording in
`public_tests/README.md:27-30` and `sealed/DESIGN.md:77-78` is not universally
true. `benchmarks/router-benchmark.js:95-107` directly invokes the target in a
bounded iteration loop but has no independent elapsed-time watchdog.

## Disclosure checks

```bash
find . -path '*/sealed/*' -type f -print | sort
find . -path '*/sealed/*' -type f -print | wc -l
```

Observed: 21 files, including the full reference implementation/tests,
adversarial expectations, debugging fixed implementations/answers, and review
answers. Direct `test -r` checks returned readable for representative files in
each category. The candidate includes instructions not to inspect them, but no
reduced learner export, visibility allowlist, permission boundary, or transfer
record was supplied. Whether an external delivery layer filters these files is
therefore inconclusive.

## Credential and filesystem safety checks

The two high-confidence content scans recorded in `CANDIDATE/VALIDATION.md`
were repeated. Both produced no filenames and exited 1 (no match):

```bash
grep -RIlE -- '-----BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY-----|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-(proj-)?[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}' README.md AGENTS.md MANIFEST.yaml PROVENANCE.json LICENSE_BOUNDARY.md REQUIREMENTS.md CONCEPTS.md DESIGN_QUESTIONS.md VALIDATION.md starter public_tests environment sealed adversarial debugging review_exercises benchmarks

grep -RIlE -- '(password|passwd|api[_-]?key|access[_-]?token|client[_-]?secret)[[:space:]]*[:=][[:space:]]*[^[:space:]]{8,}' README.md AGENTS.md MANIFEST.yaml PROVENANCE.json LICENSE_BOUNDARY.md REQUIREMENTS.md CONCEPTS.md DESIGN_QUESTIONS.md VALIDATION.md starter public_tests environment sealed adversarial debugging review_exercises benchmarks
```

A filename scan for `*.pem`, `*.key`, `*credential*`, and `*secret*` produced no
output. Full inventory and `lstat` checks found no symlinks or special nodes.
Static JavaScript inspection found no child-process or dynamic-code execution;
network activity is limited to loopback HTTP in tests/harnesses.

These targeted scans reduce risk but are not a general secret detector.

## Provenance and license observations

`PROVENANCE.json` pins the catalog source ID and commit and records the linked
tutorial as `NOASSERTION`. `LICENSE_BOUNDARY.md` explicitly says the catalog's
CC0 status does not license that tutorial and claims no linked content was
fetched or copied. No third-party runtime dependency or vendored tree was
observed.

The source checkout lies outside this isolated workspace and network access is
disabled, so the source commit/hash, linked content, and no-copy assertion could
not be independently compared. The generated material has a personal-
educational-use description but no explicit SPDX reuse/distribution license.

## Result

**REVISE.** Preserve the conservative manifest labels. Correct and test the
route-local decoding-error path, provide independently validated learner-view
isolation, replace or qualify the absolute-timeout claims, and clarify generated
material licensing before promotion.
