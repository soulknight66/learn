# Independent validation record

## Scope and preservation

Commands ran from the review workspace root on 2026-08-31 unless a different working directory is
shown. `CANDIDATE/` was mounted read-only (`dr-xr-sr-x`; files `-r--r--r--`) and was never edited.
Repeated ambient `/usr/bin/id` name-resolution warnings are omitted below because they did not change
the reported command exit statuses.

The initial path-and-content aggregate was:

```text
$ find CANDIDATE -type f -exec sha256sum {} + | sort | sha256sum
d6038624f00cbe5cfbd8466f9b657ccc99ef3a7fef82c20b125723ad8e9bd2f4  -
```

After creating the three review artifacts outside `CANDIDATE/`, the same command returned the same
aggregate:

```text
d6038624f00cbe5cfbd8466f9b657ccc99ef3a7fef82c20b125723ad8e9bd2f4  -
```

The submitted material was unchanged by this review.

## Toolchain availability

```text
$ python3 --version
Python 3.6.8
exit 0

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5
exit 0

$ node --version
/bin/bash: node: command not found
exit 127

$ git status --short --branch
/bin/bash: git: command not found
exit 127
```

No executable was found under `node`, `nodejs`, `npm`, `npx`, `deno`, `bun`, `qjs`, `js`, `d8`,
`jsc`, or `quickjs`. Neither Python installation had `js2py`, `quickjs`, `py_mini_racer`, `esprima`,
or `tree_sitter` installed.

## JavaScript execution attempts

Each potentially running command had a 30-second outer bound.

```text
$ timeout 30 node --test CANDIDATE/public_tests/*.test.mjs
timeout: failed to run command 'node': No such file or directory
exit 127

$ timeout 30 node --test CANDIDATE/sealed/reference_tests/*.test.mjs
timeout: failed to run command 'node': No such file or directory
exit 127

$ timeout 30 node CANDIDATE/sealed/adversarial/run.mjs
timeout: failed to run command 'node': No such file or directory
exit 127

$ timeout 30 node CANDIDATE/sealed/benchmarks/benchmark.mjs --samples 1 --iterations 1 --warmup 0
timeout: failed to run command 'node': No such file or directory
exit 127
```

Observed result: no JavaScript file was parsed or executed. There are no independent pass counts,
coverage values, adversarial results, fuzz results, or timings.

## Supplied static checker

From `CANDIDATE/`, using the default interpreter:

```text
$ timeout 20 python3 sealed/validation/check_artifact.py
  File "sealed/validation/check_artifact.py", line 4
    from __future__ import annotations
    ^
SyntaxError: future feature annotations is not defined
exit 1
```

Using the explicitly provisioned interpreter:

```text
$ timeout 20 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/validation/check_artifact.py
required paths: 23/23 present
raw forbidden paths present: []
artifact forbidden paths present: []
artifact path types: regular files/directories only
metadata: strict JSON, exact manifest, immutable object hashes match
JavaScript modules: 26 files, 46 relative imports resolved
credential scan: 68 files, 0 high-confidence matches
STATIC VALIDATION PASS
exit 0
```

This independently observed execution corroborates only what the inspected script checks. It does not
prove any build, test, fuzz, benchmark, review, transfer, or production label. The `raw forbidden
paths` result differs from the submitted historical transcript (`['.git']`) because this review copy
has no `CANDIDATE/.git`.

## Independent metadata and structure checks

A separate inline Python 3.11 program parsed `MANIFEST.yaml`, `PROVENANCE.json`, and both package files
with duplicate-key rejection, serialized each as sorted compact JSON, and calculated SHA-256:

```text
MANIFEST.yaml 4a859f7ef29b82262ab14d0905a229ac405caa20c09a87c02d96bdb2e9889abb strict-json-ok
PROVENANCE.json 0662131d16852680e77c8aaac5c7ec76fefe6aa84c6d9373cbc196d327d66161 strict-json-ok
starter/package.json 9cc644124e4f6e60a58c9d193151fd2b72dad78f20edefd93a79644108d44335 strict-json-ok
sealed/reference/package.json 06d4da883b94dd862c0c524584c16255bb0c276ad4be79da86ed2587e6d9cc5a strict-json-ok
exit 0
```

A separate import/path walk (not the candidate checker) observed:

```text
javascript_files 26
from_imports 61
relative_imports 46
missing_relative_imports []
special_or_symlink_paths []
regular_files 68
exit 0
```

Target-wiring inspection produced:

```text
$ grep -R -n -E 'starter/src/index|reference/index' CANDIDATE/sealed CANDIDATE/public_tests --include='*.mjs'
CANDIDATE/sealed/adversarial/run.mjs:7:} from "../reference/index.js";
CANDIDATE/sealed/benchmarks/benchmark.mjs:10:} from "../reference/index.js";
CANDIDATE/sealed/reference_tests/pebble-reference.test.mjs:25:} from "../reference/index.js";
CANDIDATE/public_tests/01-tokenize.test.mjs:4:import { TokenType, tokenize } from "../starter/src/index.js";
CANDIDATE/public_tests/02-parse.test.mjs:4:import { parse, tokenize } from "../starter/src/index.js";
CANDIDATE/public_tests/03-tree.test.mjs:4:import { evaluate, parse, run } from "../starter/src/index.js";
CANDIDATE/public_tests/04-vm.test.mjs:4:import { compile, execute, parse, run } from "../starter/src/index.js";
CANDIDATE/public_tests/05-errors.test.mjs:11:} from "../starter/src/index.js";
exit 0
```

Recursive source searches found no JavaScript match for `eval(`, `Function(`, `node:vm`, or child
process APIs, and no high-confidence private-key, AWS, GitHub, OpenAI-style, or Slack credential
pattern. These are bounded pattern checks, not comprehensive security or secret-scanning evidence.

## Manual contract traces

- The starter is intentionally incomplete: lexer, parser, evaluator, compiler, and VM entry points
  throw `PebbleNotImplementedError`. That is appropriate learner scaffolding and means public failures
  would be expected; it is not treated as a submitted solution claiming to pass.
- For `emit 1;` at `maxSteps: 2`, the sealed tree evaluator charges the statement and literal (two
  ticks) and returns `[1]`. The sealed VM compiles `CONSTANT`, `EMIT`, `HALT`; it charges the first two
  and raises `STEP_LIMIT_EXCEEDED` before fetching `HALT`. This trace establishes the documented
  backend cutoff ambiguity without claiming a runtime execution.
- The complete candidate tree contains readable sealed reference code, sealed tests, six answer keys,
  and later-stage prompt directories. No generated learner view or reveal-policy artifact was present
  to validate the stated withholding behavior.
- The manifest says `GENERATED` and `PARTIAL`, requires independent validation, and sets
  `productionized` to `false`. Prose explicitly disclaims unrun testing, fuzzing, benchmarking, and
  production readiness; no dishonest label promotion was found.

## Limitations

- JavaScript syntax, loading, behavior, tests, adversarial cases, and benchmarks are inconclusive
  because no JavaScript runtime or parser was available.
- The upstream linked repository and immutable source snapshot were outside the permitted workspace;
  no-copy, close-paraphrase, and linked-resource-license claims could not be independently compared.
- Only the complete administrator candidate was supplied. The behavior of any external learner-view
  projector, staged reveal service, or transfer validator could not be observed.
- Static inspection cannot establish robustness against deep recursion, memory exhaustion, malicious
  objects/getters, or all malformed bytecode paths.
- The supplied checker is builder-authored evidence. Its successful rerun was recorded, but it was not
  used to infer `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or
  `PRODUCTIONIZED`.
