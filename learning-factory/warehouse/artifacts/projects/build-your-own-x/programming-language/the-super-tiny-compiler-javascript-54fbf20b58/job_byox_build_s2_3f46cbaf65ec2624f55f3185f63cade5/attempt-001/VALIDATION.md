# Validation record

Recorded in the allocated generation workspace on 2026-09-02 (America/Chicago). This is generation evidence only. Independent validation remains required, and the artifact status remains `GENERATED` + `PARTIAL`.

## Target runtime blocker

Exact command:

```text
node --version
```

Observed exit 127:

```text
/bin/bash: node: command not found
```

Exact command:

```text
npm --version
```

Observed exit 127:

```text
/bin/bash: npm: command not found
```

The intended test commands were attempted exactly as follows:

```text
node --test public_tests/compiler.test.js
node --test sealed/reference_tests/compiler.test.js sealed/reference_tests/bytecode.test.js sealed/reference_tests/production.test.js
```

Each exited 127 with `/bin/bash: node: command not found`. Consequently, the authoritative `node:test` suites were **not executed**, no npm installation was attempted, and no `TESTED` or `BUILDS` label is claimed.

## Available-runtime smoke validation

Exact command and observed result:

```text
$ gjs --version
gjs 1.56.2
```

GJS is not the target Node environment, but it can execute the dependency-free compiler core. A first run of the fallback suite exposed an incorrect expectation in the new fallback test itself:

```text
$ gjs sealed/reference_tests/gjs-smoke.js
JS ERROR: Error: assertion failed: token location: {"line":2,"column":1,"offset":25}
```

The expected offset was corrected from 28 to 25. A second run reached the production wrapper but reported `ReferenceError: Buffer is not defined`; the GJS-only CommonJS adapter was corrected to pass its documented UTF-8 `Buffer.byteLength` shim into loaded modules. The final exact command and observed result were:

```text
$ gjs sealed/reference_tests/gjs-smoke.js
GJS_SMOKE_PASS assertions=35
```

That smoke suite exercised scanning, locations, precedence, structured failures, analysis, interpretation, optimized and unoptimized generation, optimizer purity, negative zero, non-finite folding policy, short-circuiting, injection containment, the bytecode alternative, and compile-size limits.

## JavaScript syntax pass

Every generated `.js` file was parsed as a function body by the available SpiderMonkey engine. Shebangs were removed before parsing. Exact command:

```text
find . -type f -name '*.js' -exec gjs -c 'const GLib=imports.gi.GLib; const ByteArray=imports.byteArray; const loaded=GLib.file_get_contents(ARGV[0]); let source=ByteArray.toString(loaded[1]); if (source.startsWith("#!")) source=source.slice(source.indexOf("\n")+1); Function(source); print("SYNTAX_OK " + ARGV[0]);' {} \;
```

Observed exit 0 with `SYNTAX_OK` for all 19 JavaScript files: starter, public tests, reference and CLI, four sealed reference-test files, bytecode backend, production wrapper, adversarial suite, benchmark driver, and both debugging/review exercise variants and tests.

## Immutable JSON check

Python's strict JSON loader was used with a duplicate-key-rejecting object hook. `MANIFEST.yaml` was compared as an object to the complete mandated object. Provenance top-level and nested key sets, immutable IDs, hashes, license boundary, concepts, commit, and null upstream URL were asserted.

Observed exit 0:

```text
STRICT_JSON_OK manifest_exact=true provenance_structure=true duplicate_keys=false
```

The saved reproducible checker combines those assertions with canonical immutable-provenance content, archive boundaries, regular-file checks, and credential signatures. Exact command and observed exit 0 result:

```text
$ python3 sealed/reference_tests/validate_artifact.py
ARTIFACT_CHECK_OK required=23 forbidden=21 generated_files=48 credential_matches=0 manifest_status=GENERATED labels=GENERATED,PARTIAL
```

## Credential-pattern scan

Factory-owned dot paths were excluded rather than inspected. Exact command:

```text
find . -type f ! -path './.agents/*' ! -path './.codex/*' ! -path './.factory-workspace' -exec grep -nHE -- '-----BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|(api[_-]?key|access[_-]?token|password|passwd)[[:space:]]*[:=][[:space:]]*[A-Za-z0-9/+_=.-]{12,}' {} +
```

Observed exit 1 with no matching lines, which is grep's no-match result.

## Required, forbidden, and file-type checks

The authoritative required and forbidden arrays were loaded into Bash arrays. Each required path was checked with `-f` and rejected if `-L`; each forbidden path was checked with both `-e` and `-L`. The complete workspace was then scanned with:

```text
find . ! -type f ! -type d -print
```

Observed exit 0 summary:

```text
REQUIRED_CHECK count=23 failures=0
FORBIDDEN_CHECK count=21 present=0
TYPE_CHECK unexpected=0
```

Thus every authoritative path is a regular file, no forbidden path exists, and no symlink, device, socket, FIFO, or other special path exists in the workspace.

## Validation boundary

No network access, upstream fetch, package installation, benchmark run, randomized fuzzing, profiler, or production deployment was performed. The benchmark driver records results only when actually run. `sealed/production/PRODUCTIONIZATION.md` lists known blockers. Independent validators must run the target Node suites and decide all stronger labels.
