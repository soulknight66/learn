# Independent validation record

Review date: 2026-09-02 (America/Chicago). Commands were run from `CANDIDATE/` unless a command explicitly names that directory. `CANDIDATE/` was treated as immutable.

## Runtime availability

```text
$ timeout 10s node --version
timeout: failed to run command ‘node’: No such file or directory
exit 127

$ gjs --version
gjs 1.56.2
exit 0

$ python3 -c 'import sys; print(sys.version)'
3.6.8 ...
exit 0
```

Executable lookup also returned `None` for `node` and `npm`. Therefore no Node command below was represented as executed, and no `BUILDS` or `TESTED` conclusion was drawn.

## Submitted checks (corroborative only)

These scripts were authored with the candidate. Their successful execution is useful corroboration, but their assertions and prose were independently inspected and were not treated as proof by themselves.

```text
$ timeout 15s python3 sealed/reference_tests/validate_artifact.py
ARTIFACT_CHECK_OK required=23 forbidden=21 generated_files=48 credential_matches=0 manifest_status=GENERATED labels=GENERATED,PARTIAL
exit 0

$ timeout 20s gjs sealed/reference_tests/gjs-smoke.js
GJS_SMOKE_PASS assertions=35
exit 0
```

## JavaScript syntax

```text
$ timeout 30s find . -type f -name '*.js' -exec gjs -c 'const GLib=imports.gi.GLib; const ByteArray=imports.byteArray; const loaded=GLib.file_get_contents(ARGV[0]); let source=ByteArray.toString(loaded[1]); if (source.startsWith("#!")) source=source.slice(source.indexOf("\n")+1); Function(source); print("SYNTAX_OK " + ARGV[0]);' {} \;
```

Observed: exit 0 and `SYNTAX_OK` for all 19 JavaScript files. This checks parsing with SpiderMonkey/GJS, not Node module resolution or `node:test` execution.

## Reviewer-authored semantic differential

Invocation:

```text
$ timeout 45s gjs -c '<reviewer-authored inline CommonJS loader and differential harness>'
INDEPENDENT_GJS_CHECK_PASS checks=1680 programs=836
exit 0
```

The harness loaded `sealed/reference/compiler.js` directly, then for every combination of eight representative literals and all thirteen binary operators compared:

1. `interpret(source)`;
2. `Function(compile(source))()`; and
3. `Function(compile(source, { optimize: false }))()`.

That accounts for 832 generated programs. Four targeted programs added all builtins, Unicode `len`, skipped `len` type failures, and bindings named `class`, `await`, `constructor`, and `__proto__`. Additional assertions checked known values, structured lex/parse codes and offsets, node locations, input preservation during optimization, distinct optimized identity, and safe lowering/execution of a handcrafted declaration name containing active JavaScript text. NaN and negative zero comparisons used `Object.is` semantics.

## Reviewer-authored limits and alternative-backend checks

```text
$ timeout 20s gjs -c '<reviewer-authored inline limits and bytecode harness>'
INDEPENDENT_LIMIT_BYTECODE_PASS checks=16
exit 0
```

Observed checks covered `maxSourceBytes`, `maxTokens`, `maxAstNodes`, and `maxGeneratedBytes`; error type and fields; deterministic returned metrics; malformed and unknown limit configuration; generated result 42; bytecode operand-valued short-circuiting; and the bytecode step budget.

## Reviewer-authored adversarial checks

```text
$ timeout 20s gjs -c '<reviewer-authored inline scanner and long-expression harness>'
INDEPENDENT_ADVERSARIAL_PASS ascii=128 flat_terms=1500
exit 0
```

Each single ASCII code point either produced a token stream ending in EOF or a structured lexical `CompilerError`. CRLF location fields were checked. A deterministic 1,500-term addition expression then passed parsing, interpretation with result 1500, optimized compilation, and generated execution with result 1500.

## Structure, provenance, and credential boundary

Independent observations:

```text
$ find . -type l -print
<no output>
exit 0

$ find . ! -type f ! -type d -print
<no output>
exit 0

$ python3 <strict duplicate-key and canonical-hash check>
STRICT_JSON_NO_DUPLICATES MANIFEST.yaml,PROVENANCE.json
canonical_provenance_sha256=00c0f1953c40ad885d5f54109afec5975f816ee6403ff8414d7e81639bade85e
manifest_snapshot_match=True
manifest_status=GENERATED
labels=GENERATED,PARTIAL
productionized=False
exit 0

$ grep -RInE --exclude=VALIDATION.md --exclude=validate_artifact.py -- '<common private-key, cloud-key, token, and password signatures>' .
<no output>
exit 1 (grep no-match)

$ grep -RInE 'https?://' .
./PROVENANCE.json:48:    "upstream_reference": "https://github.com/jamiebuilds/the-super-tiny-compiler"
exit 0
```

An initial credential-scan invocation omitted grep's `--` pattern delimiter and exited 2 with an option-parsing error. The corrected command above was then run and is the only credential-scan result used.

Raw file hashes observed:

```text
b12862e28bf7258cea6316c3999310d04ea263057e38811318ebe989fcc5422d  MANIFEST.yaml
45dd14579d697467853a12ac11a6cb668748b70306e5d69e2997fee4ffaa1ad4  PROVENANCE.json
7a52fd72324e5d1a65263900cef1db780bb571ed0bf1b6c0c86ae15c1a7e7831  LICENSE_BOUNDARY.md
```

The deterministic candidate-tree digest (relative path plus each file's SHA-256) was computed before and after writing the three review artifacts:

```text
CANDIDATE_TREE_SHA256=b09fd18b239aeaaff83e43fbb5c083e5ed7e9273d9dfa86dcd7ce67a79a65457
```

The matching values confirm that this review did not modify `CANDIDATE/`.

## Review artifact self-check

```text
$ python3 -c '<exact-key/type/enum assertions for EVALUATION.json>'
EVALUATION_SCHEMA_OK verdict=PASS checks=9 evidence=8 limitations=5
exit 0

$ find . -maxdepth 1 -type f -printf '%f\n'
.factory-workspace
EVALUATION.json
REVIEW.md
VALIDATION.md
exit 0
```

## Unavailable or inconclusive checks

- `node --check`, all `node:test` suites, and the Node CLI were not run because Node.js is unavailable.
- The source/catalog baseline and upstream linked project were unavailable; recorded hashes and the no-copy claim could not be externally re-derived.
- The reviewer workspace exposes sealed content. Actual student-view exclusion and transfer behavior belong to the external learning harness and were not observable here.
- No randomized fuzzing, benchmark, profiler, network, deployment, or production-security check was run.
- No stronger validation label was assigned. The advisory `PASS` in `EVALUATION.json` requires a separate orchestrator-captured acceptance validator before any `REVIEWED` promotion.
