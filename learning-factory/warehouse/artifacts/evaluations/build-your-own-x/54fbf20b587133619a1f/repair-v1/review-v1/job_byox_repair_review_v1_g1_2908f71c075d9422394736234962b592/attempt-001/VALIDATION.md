# Independent validation record

Review date: 2026-08-31. Commands ran from the provided review workspace unless a different working
directory is shown. `CANDIDATE/` was treated as read-only throughout.

## Inventory and immutability

```sh
find CANDIDATE -type f -exec sha256sum {} + | sort | sha256sum
find CANDIDATE -type f | wc -l
find CANDIDATE -type l -print
find CANDIDATE \! -type f \! -type d -print
```

Observed:

```text
7bb404607798ca0af350d9e2841965a50054ce6e6ce8f28d444bd478c93b8e5c  -
74
(no symbolic links)
(no special paths)
```

The same aggregate was observed after validation and after writing the review files. No candidate
file changed. A temporary projected view was the only generated test material and was deleted after
inspection.

`rg` and `git` were unavailable (`command not found`), so inventory used `find` and repository history
or status could not be inspected.

## Runtime availability and bounded JavaScript attempts

```sh
for runtime_name in node nodejs deno bun qjs js d8 jsc quickjs npm npx; do
  runtime_path=$(command -v "$runtime_name" 2>/dev/null || true)
  if [ -n "$runtime_path" ]; then
    printf '%s=%s\n' "$runtime_name" "$runtime_path"
  else
    printf '%s=not-found\n' "$runtime_name"
  fi
done
python3 --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed: every JavaScript/runtime-package name was `not-found`; the Python versions were 3.6.8 and
3.11.5.

Each attempted JavaScript command had an outer bound:

```sh
timeout 5 node --version
timeout 30 node --test CANDIDATE/public_tests/01-tokenize.test.mjs
timeout 30 node --test CANDIDATE/sealed/reference_tests/pebble-reference.test.mjs
timeout 30 node CANDIDATE/sealed/adversarial/run.mjs
timeout 30 node CANDIDATE/sealed/benchmarks/benchmark.mjs --samples 1 --iterations 1 --warmup 0
```

Every command observed `timeout: failed to run command 'node': No such file or directory` and exit
status `127`. No JavaScript was parsed or executed. There is no observed public/reference pass count,
differential result, fuzz result, or benchmark result.

No installed Python JavaScript parser fallback was found: `esprima`, `tree_sitter`,
`tree_sitter_javascript`, `pyjsparser`, `quickjs`, and `js2py` all resolved false through
`importlib.util.find_spec`.

## Submitted Python validators

From `CANDIDATE/`:

```sh
PYTHONDONTWRITEBYTECODE=1 timeout 20 python3 sealed/validation/check_artifact.py
PYTHONDONTWRITEBYTECODE=1 timeout 20 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/validation/check_artifact.py
```

Both exited `0` and independently observed the same submitted output:

```text
required paths: 23/23 present
raw forbidden paths present: []
artifact forbidden paths present: []
artifact path types: regular files/directories only
metadata: strict JSON, exact manifest, immutable object hashes match
JavaScript modules: 27 files, 46 relative imports resolved
evaluator binding: fixed candidate and oracle entries with artifact identities
evaluator artifacts: algorithm=path-content-sha256-v1 candidate=c8014bfeaec5dcf7d7a9ae40a873a495f07806f608bef6aac9b08441d8c61ee1 oracle=ddb6c95a9e6c26dafa217e8f300cc589d77e56c11cb7e2b6103096a3f0ca1942
learner views: 5 default-deny cumulative stages audited; sealed paths absent
credential scan: 74 files, 0 high-confidence matches
STATIC VALIDATION PASS
```

These are executions of candidate-supplied checks, so the result proves only their implemented
assertions. The checker explicitly does not parse JavaScript or establish runtime behavior.

```sh
PYTHONDONTWRITEBYTECODE=1 timeout 20 \
  python3 -m unittest discover -s sealed/validation -p 'test_*.py' -v
```

Observed: all 8 tests passed in 0.121 seconds; exit `0`.

```sh
PYTHONDONTWRITEBYTECODE=1 timeout 20 python3 sealed/validation/view_policy.py audit
```

Observed:

```text
core files=25 sha256=4f29447b49455e0decd6a0f26c5fc5c60e895437eaaea0545f682e5d0201e846
debugging files=29 sha256=091bb90b13174034cfe721cbbff03c2d3613d41e0b483d2fa80b37e925fb800b
review files=33 sha256=c093c9d32852b096533ba58a8d411ffb09d315f81ef7b6aef15581cf23642d2a
adversarial files=34 sha256=e677361cf4fa6317cf9ee1e01e202af474424ebc8931d3f9a61fbb1ccf77986e
benchmarks files=35 sha256=6d03f851876c217512f6493d7484b2ee0e5ba6a7ae3dc00c9077adf5dfb7dfa3
VIEW POLICY AUDIT PASS
```

## Independent view reconstruction and materialization

A separate Python 3.11 here-document strictly loaded `view-policy.json`, independently walked every
cumulative allowlisted root with `lstat`, rejected non-regular paths, reconstructed sorted
path/content records, and recalculated each digest:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
import hashlib, json, stat
from pathlib import Path
root = Path('CANDIDATE').resolve()

def no_dupes(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AssertionError(key)
        result[key] = value
    return result

policy = json.loads(
    (root / 'environment/view-policy.json').read_text(encoding='utf-8'),
    object_pairs_hook=no_dupes,
)
assert policy['default_action'] == 'deny'
assert policy['follow_symlinks'] is False
roots, previous = list(policy['learner_base']), set()
for stage in policy['stages']:
    roots.extend(stage['reveal'])
    paths = set()
    for relative_root in roots:
        start = root / relative_root
        candidates = [start] if start.is_file() else list(start.rglob('*'))
        for path in candidates:
            mode = path.lstat().st_mode
            assert stat.S_ISREG(mode) or stat.S_ISDIR(mode)
            if stat.S_ISREG(mode):
                paths.add(path.relative_to(root).as_posix())
    assert previous <= paths
    previous = paths
    records = [[p, hashlib.sha256((root / p).read_bytes()).hexdigest()]
               for p in sorted(paths)]
    digest = hashlib.sha256(
        json.dumps(records, ensure_ascii=False, separators=(',', ':')).encode()
    ).hexdigest()
    forbidden = {'sealed', 'VALIDATION.md', 'PROVENANCE.json', 'LICENSE_BOUNDARY.md'} & {
        p.split('/', 1)[0] for p in paths
    }
    print(stage['name'], len(paths), digest, sorted(forbidden))
PY
```

Observed the same five counts and digests shown above, with `[]` for forbidden roots at every stage.

The projector was also exercised against a new temporary path outside `CANDIDATE/`:

```sh
review_tmp=$(mktemp -d "$PWD/.review-projection.XXXXXX")
review_out="$review_tmp/core"
PYTHONDONTWRITEBYTECODE=1 timeout 20 \
  python3 CANDIDATE/sealed/validation/view_policy.py export core "$review_out"
find "$review_out" -type f | wc -l
find "$review_out" -mindepth 1 -maxdepth 1 \
  \( -name sealed -o -name VALIDATION.md -o -name PROVENANCE.json \
     -o -name LICENSE_BOUNDARY.md -o -name debugging -o -name review_exercises \
     -o -name adversarial -o -name benchmarks \) -print
```

Observed:

```text
exported core files=25 sha256=4f29447b49455e0decd6a0f26c5fc5c60e895437eaaea0545f682e5d0201e846
25
(no forbidden top-level output)
```

The validated temporary directory was then removed. This checks local projector behavior only, not
the production learner transfer boundary.

## Metadata and license/provenance consistency

A strict independent JSON parse and canonical hash calculation observed:

```text
manifest_canonical_sha256=4a859f7ef29b82262ab14d0905a229ac405caa20c09a87c02d96bdb2e9889abb
provenance_canonical_sha256=0662131d16852680e77c8aaac5c7ec76fefe6aa84c6d9373cbc196d327d66161
ids_match=True
manifest_pointer_matches_snapshot_field=True
catalog_license=CC0-1.0
linked_resource_license=NOASSERTION
ingested_utc=2026-08-30T20:47:36.953276+00:00
```

The project ID, source ID, and source commit agree across manifest and provenance fields. The linked
project URL appears only in administrator provenance. The external catalog/source trees were not
readable, so the recorded source commit, license evidence, and no-copy assertion were not independently
verified against upstream content.

## Evaluator-boundary probe

The boundary patterns from `sealed/evaluator/bindings.mjs` were applied to three legal
comment-separated import spellings:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
import re
patterns = {
    'from': re.compile(r'\b(?:from)\s*["\']([^"\']+)["\']'),
    'side_effect': re.compile(r'\bimport\s*["\']([^"\']+)["\']'),
    'dynamic': re.compile(r'\bimport\s*\('),
}
probes = {
    'commented_static':
        'import { run } from/* comment */ "../../sealed/reference/index.js";',
    'commented_side_effect':
        'import/* comment */ "../../sealed/reference/index.js";',
    'commented_dynamic':
        'const oracle = await import/* comment */("../../sealed/reference/index.js");',
}
for name, source in probes.items():
    print(name, {kind: bool(pattern.search(source))
                 for kind, pattern in patterns.items()})
PY
```

Observed:

```text
commented_static {'from': False, 'side_effect': False, 'dynamic': False}
commented_side_effect {'from': False, 'side_effect': False, 'dynamic': False}
commented_dynamic {'from': False, 'side_effect': False, 'dynamic': False}
```

The current starter was separately scanned and inspected; it contains no such escape and no learner
implementation using `eval`, `Function`, Node `vm`, or child processes. The finding concerns the
trustworthiness of the harness when it later loads untrusted learner code.

## Static implementation review

The following were inspected line by line: the normative requirements; all starter modules and public
tests; all reference modules and reference tests; evaluator bindings; adversarial cases/runner;
benchmark harness; view projector/checker/tests; staged prompts and sealed answers; provenance,
license, design, review, trade-off, and production notes.

Static tracing found the lexer/parser/compiler/evaluator design internally coherent for ordinary
inputs, but it cannot replace execution. It also confirmed two documented gaps:

- `validateBytecode` performs shape/operand checks before dispatch, while stack underflow and final
  stack height are checked only during execution; no control-flow stack analysis is present.
- Parser, evaluator, and compiler expression walks are recursive and have no explicit nesting bound.

The evaluator isolation issue was not disclosed as a limitation in the candidate and is the primary
reason for the `REVISE` verdict.
