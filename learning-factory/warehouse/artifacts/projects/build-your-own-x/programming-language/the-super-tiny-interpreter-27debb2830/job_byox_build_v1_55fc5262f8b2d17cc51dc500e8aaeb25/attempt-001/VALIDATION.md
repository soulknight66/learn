# Validation record

Artifact status remains `GENERATED` + `PARTIAL`. Independent validation is required. This record was
created on 2026-08-31 in the allocated factory workspace.

## Supported static checks

Command from repository root:

```sh
python3 environment/verify_artifact.py
```

Observed output (exit status 0):

```text
artifact verification: PASS (23 required paths, 0 forbidden paths)
JSON and credential-pattern scans: PASS
lightweight JavaScript delimiter scan: PASS (31 files; not a syntax check)
```

The checker verifies required regular files, absence of every forbidden path, exact manifest data,
key provenance bindings, JSON parsing, a credential-pattern scan over generated text, and balanced
JavaScript delimiters. The delimiter scan is explicitly not an ECMAScript syntax check.

## JavaScript runtime availability

Commands attempted from repository root:

```sh
node --version
npm --version
```

Observed result for each: `/bin/bash: node: command not found` and
`/bin/bash: npm: command not found`, respectively (exit status 127). Additional `command -v` probes found
no `nodejs`, `deno`, `bun`, `qjs`, `js`, `quickjs`, `jjs`, or `d8`. Python 3.6.8 was available.
No network access or dependency installation was attempted.

An additional static-parser probe was attempted:

```sh
python3 -c "import esprima; print(esprima.__version__)"
```

It failed with `ModuleNotFoundError: No module named 'esprima'` (exit status 1), so the validation
record makes no JavaScript syntax claim.

A later probe found GJS 1.56.2 (SpiderMonkey JavaScript-C60.9.0). Exact attempts were:

```sh
gjs sealed/reference/src/index.js
gjs -m sealed/reference/src/index.js
```

The first rejected the top-level import because GJS treated the file as a classic script (exit 1).
The second reported `Unknown option -m` (exit 133). This legacy shell therefore could not load the
ES modules or run the Node-specific tests; those direct attempts provide no execution evidence.

## Supplemental legacy-shell smoke

Command from repository root:

```sh
python3 sealed/reference_tests/gjs_bundle.py | gjs /dev/stdin
```

Observed output (exit status 0):

```text
GJS_TRANSPILED_SMOKE_PASS
```

The Python helper reads the sealed reference modules, removes ESM import/export syntax, isolates each
module in a wrapper, and mechanically downlevels numeric separators, optional access, nullish access,
and `Array.at` for SpiderMonkey JavaScript-C60.9.0. It writes only to the pipe. The smoke assertions
cover token locations, tree/VM arithmetic parity, loops, scope, short-circuiting, conditionals, typed
lex/parse/runtime errors, and malformed-bytecode rejection.

This is partial algorithm evidence only. Because the executed stream is transformed, it does not
establish that the original files parse as ECMAScript modules, that imports/exports link in Node.js,
or that any `node:test` file passes. It earns no validation label.

## Test attempts

These commands are the intended test entry points:

```sh
cd starter && npm test
cd starter && npm run test:public
cd sealed/reference && npm test
```

Observed result for all three commands: `/bin/bash: npm: command not found` (exit status 127).
The factory shell also emitted unrelated user/group name lookup warnings before command output.
No JavaScript assertion executed. Test files must not be described as passing until an independent
runtime executes them.

## Not performed

No fuzzing, benchmark execution, profiler run, coverage collection, transfer validation, external
upstream access, dependency installation, security audit, or production deployment was performed.
The benchmark harness contains no fabricated measurements. `productionized` remains false.
