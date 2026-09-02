# Repair-generation validation evidence

Validation date: 2026-09-02. Commands ran from the repaired pack root. This is fresh generation-2
evidence; results archived in `PRIOR_BUILD/` or `PRIOR_REVIEW/` are not treated as executions here. The
launcher emitted user/group lookup warnings from `/usr/bin/id` before commands; those environmental
warnings are omitted from observations below.

The pack remains `GENERATED` + `PARTIAL`. These builder-run checks do not grant any independent
validation label.

## Toolchains

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed, exit 0:

```text
Python 3.11.5
```

```bash
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
```

Observed, exit 0:

```text
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
```

Java was available but was not useful for this standard-library Python pack. `rg` was unavailable on
`PATH`, so bounded `find`, `grep`, and Python standard-library checks were used.

## Runtime preflight

```bash
TMPDIR=environment /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/check_runtime.py
```

Observed, exit 0:

```text
runtime_ok python=3.11.5 tempdir=<workspace>/environment
```

`<workspace>` abbreviates only the allocated absolute workspace prefix printed by the check.

## Repair regressions

The focused command below was run after adding the contract, predicate, and learner-boundary regressions:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest \
  public_tests.test_language_contract.LanguageContractTests.test_empty_predicate_accepts_every_value \
  sealed.reference_tests.test_interpreter_reference.InterpreterReferenceTests.test_empty_predicate_is_total_across_value_kinds \
  sealed.reference_tests.test_learner_view.LearnerViewTests.test_learner_facing_provenance_and_license_guidance_is_self_contained \
  sealed.reference_tests.test_learner_view.LearnerViewTests.test_supplemental_roots_have_no_learner_reveal_stage -v
```

The first run observed 4 tests with 1 failure, exit 1: a documentation assertion expected a contiguous
singular phrase while the complete non-copy statement used a line-broken plural phrase. After making the
learner summary's non-copy sentence explicit, the second run again observed 4 tests with 1 failure, exit
1: an assertion expected `does not grant rights` while the text correctly said `does not assert a license
for, or grant rights`. The assertion was narrowed to that exact policy statement. The third run observed,
exit 0:

```text
Ran 4 tests in 0.074s
OK
```

No implementation failure was hidden by those edits: the two `empty?` tests passed in all three runs.

The resolved behavior was also probed directly:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
from pebble import Interpreter, format_value
interpreter = Interpreter(output=lambda _text: None)
for source in ('(empty? nil)', "(empty? '())", "(empty? '(1))", '(empty? 1)',
               '(empty? false)', '(empty? "")', '(empty? +)',
               '(empty? (fn () nil))'):
    print(source + ' -> ' + format_value(interpreter.eval_source(source)))
PY
```

Observed, exit 0:

```text
(empty? nil) -> true
(empty? '()) -> true
(empty? '(1)) -> false
(empty? 1) -> false
(empty? false) -> false
(empty? "") -> false
(empty? +) -> false
(empty? (fn () nil)) -> false
```

## Supplied suites

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=environment PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v
```

Observed, exit 0:

```text
Ran 24 tests in 0.651s
OK
```

```bash
PYTHONDONTWRITEBYTECODE=1 TMPDIR=environment PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/reference_tests -v
```

Observed, exit 0:

```text
Ran 66 tests in 1.124s
OK
```

The intentionally incomplete starter was measured without treating its expected failure as a validation
success:

```bash
TMPDIR=environment PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'import io, unittest; suite=unittest.defaultTestLoader.discover("public_tests"); result=unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite); print(f"tests_run={result.testsRun} failures={len(result.failures)} errors={len(result.errors)} successful={result.wasSuccessful()}")'
```

Observed (the reporting command exited 0):

```text
tests_run=24 failures=5 errors=24 successful=False
```

## Canonical pack, policy, and credential audit

This audit is explicitly scoped to the factory-selected pack roots, excluding staged repair inputs and
factory workspace metadata. The fingerprint excludes this evidence file to avoid a self-referential hash.

```bash
PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
from pathlib import Path
import ast, hashlib, json, os, re

root = Path('.')
top_files = ('AGENTS.md', 'CONCEPTS.md', 'DESIGN_QUESTIONS.md',
             'LICENSE_BOUNDARY.md', 'MANIFEST.yaml', 'PROVENANCE.json',
             'README.md', 'REQUIREMENTS.md', 'VALIDATION.md')
top_dirs = ('adversarial', 'benchmarks', 'debugging', 'environment',
            'public_tests', 'review_exercises', 'sealed', 'starter')
required = ('README.md', 'AGENTS.md', 'MANIFEST.yaml', 'PROVENANCE.json',
            'LICENSE_BOUNDARY.md', 'REQUIREMENTS.md', 'CONCEPTS.md',
            'DESIGN_QUESTIONS.md', 'VALIDATION.md', 'starter/README.md',
            'public_tests/README.md', 'environment/README.md',
            'sealed/reference/README.md', 'sealed/reference_tests/README.md',
            'sealed/DESIGN.md', 'sealed/TRADEOFFS.md', 'sealed/REVIEW.md',
            'sealed/alternatives/README.md',
            'sealed/production/PRODUCTIONIZATION.md', 'adversarial/README.md',
            'debugging/README.md', 'review_exercises/README.md',
            'benchmarks/README.md')
forbidden = ('.git', '.env', '.venv', 'credentials.json', 'secrets',
             'reference', 'reference_tests', 'hidden_tests', 'solution',
             'solutions', 'answers', 'starter/sealed', 'starter/reference',
             'starter/reference_tests', 'starter/solution',
             'starter/solutions', 'starter/answers', 'public_tests/sealed',
             'public_tests/reference', 'public_tests/hidden_tests',
             'environment/sealed')
kind_errors = [name for name in top_files if not (root / name).is_file() or
               (root / name).is_symlink()]
kind_errors += [name for name in top_dirs if not (root / name).is_dir() or
                (root / name).is_symlink()]
missing = [name for name in required if not (root / name).is_file() or
           (root / name).is_symlink()]
present = [name for name in forbidden if os.path.lexists(root / name)]
entries = []
for name in top_files + top_dirs:
    path = root / name
    entries.append(path)
    if path.is_dir():
        entries.extend(path.rglob('*'))
unusual = [path.as_posix() for path in entries if path.is_symlink() or
           (not path.is_file() and not path.is_dir())]
files = sorted((path for path in entries if path.is_file()),
               key=lambda path: path.as_posix())
fingerprint = hashlib.sha256()
for path in files:
    if path == root / 'VALIDATION.md':
        continue
    relative, payload = path.as_posix().encode(), path.read_bytes()
    fingerprint.update(len(relative).to_bytes(8, 'big') + relative)
    fingerprint.update(len(payload).to_bytes(8, 'big') + payload)
patterns = (re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
            re.compile(r'AKIA[0-9A-Z]{16}'),
            re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
            re.compile(r'(?i)\b(?:api[_-]?key|password|secret|access[_-]?token)\b\s*[:=]\s*[\'\"][^\'\"]{8,}[\'\"]'))
credentials, syntax_files, calls = [], [], []
for path in files:
    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        continue
    if any(pattern.search(text) for pattern in patterns):
        credentials.append(path.as_posix())
    if path.suffix == '.py':
        syntax_files.append(path)
        tree = ast.parse(text, filename=path.as_posix())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id in {'eval', 'exec', 'compile'}:
                calls.append(f'{path}:{node.lineno}:{node.func.id}')
            if any(keyword.arg == 'shell' and isinstance(keyword.value, ast.Constant)
                   and keyword.value.value is True for keyword in node.keywords):
                calls.append(f'{path}:{node.lineno}:shell=True')
manifest = json.loads((root / 'MANIFEST.yaml').read_text(encoding='utf-8'))
provenance = json.loads((root / 'PROVENANCE.json').read_text(encoding='utf-8'))
def digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()
print(f'top_level_kind_errors={kind_errors} missing_required={missing}')
print(f'present_forbidden={present} unusual_entries={unusual}')
print(f'pack_files={len(files)} content_tree_excluding_validation_sha256={fingerprint.hexdigest()}')
print(f'syntax_ok_files={len(syntax_files)} forbidden_execution_calls={calls}')
print(f'credential_findings={credentials}')
print(f'manifest_sha256={digest(manifest)} status={manifest["status"]} labels={manifest["validation_labels"]} productionized={manifest["productionized"]}')
print(f'provenance_sha256={digest(provenance)} snapshot={provenance["snapshot_sha256"]}')
PY
```

Observed, exit 0:

```text
top_level_kind_errors=[] missing_required=[]
present_forbidden=[] unusual_entries=[]
pack_files=64 content_tree_excluding_validation_sha256=f4934ef895e2ce82db31668cbd61191dc0ac27a179cb069f6a4e244eba64842b
syntax_ok_files=33 forbidden_execution_calls=[]
credential_findings=[]
manifest_sha256=0a134783939d3d2bd9fc51f0ab33ef43cb40e4c86dc52feceb41248b0886b18e status=GENERATED labels=['GENERATED', 'PARTIAL'] productionized=False
provenance_sha256=17238e9005ea6ad305702b2fd5f18b9693608e3ccf4bf89881f929bb46002422 snapshot=7b06f5c8326e5b149cb21eca38df244194501c4ffb93c9a997e5e2f897a561bc
```

## Prior-pack preservation

The following compares path kinds and file bytes only within the 17 selected artifact roots:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
from pathlib import Path
top = ('AGENTS.md', 'CONCEPTS.md', 'DESIGN_QUESTIONS.md',
       'LICENSE_BOUNDARY.md', 'MANIFEST.yaml', 'PROVENANCE.json', 'README.md',
       'REQUIREMENTS.md', 'VALIDATION.md', 'adversarial', 'benchmarks',
       'debugging', 'environment', 'public_tests', 'review_exercises',
       'sealed', 'starter')
expected_changed = {'README.md', 'REQUIREMENTS.md', 'VALIDATION.md',
    'adversarial/README.md', 'benchmarks/README.md', 'debugging/README.md',
    'public_tests/test_language_contract.py', 'review_exercises/README.md',
    'sealed/production/PRODUCTIONIZATION.md',
    'sealed/production/learner_view.py',
    'sealed/reference/pebble/interpreter.py', 'sealed/reference_tests/README.md',
    'sealed/reference_tests/test_interpreter_reference.py',
    'sealed/reference_tests/test_learner_view.py'}
def inventory(base):
    result = {}
    for name in top:
        path = base / name
        result[name] = 'directory' if path.is_dir() else 'file'
        if path.is_dir():
            for child in path.rglob('*'):
                relative = child.relative_to(base).as_posix()
                result[relative] = 'directory' if child.is_dir() else 'file'
    return result
prior, current = inventory(Path('PRIOR_BUILD')), inventory(Path('.'))
added = sorted(current.keys() - prior.keys())
removed = sorted(prior.keys() - current.keys())
kind_changes = sorted(name for name in prior.keys() & current.keys()
                      if prior[name] != current[name])
changed = sorted(name for name in prior.keys() & current.keys()
                 if prior[name] == current[name] == 'file' and
                 (Path('PRIOR_BUILD') / name).read_bytes() != Path(name).read_bytes())
print(f'prior_entries={len(prior)} current_entries={len(current)} added={added} removed={removed} kind_changes={kind_changes}')
print(f'changed_files={changed}')
print(f'unexpected_changes={sorted(set(changed) - expected_changed)} missing_expected_changes={sorted(expected_changed - set(changed))}')
PY
```

Observed, exit 0:

```text
prior_entries=87 current_entries=87 added=[] removed=[] kind_changes=[]
changed_files=['README.md', 'REQUIREMENTS.md', 'VALIDATION.md', 'adversarial/README.md', 'benchmarks/README.md', 'debugging/README.md', 'public_tests/test_language_contract.py', 'review_exercises/README.md', 'sealed/production/PRODUCTIONIZATION.md', 'sealed/production/learner_view.py', 'sealed/reference/pebble/interpreter.py', 'sealed/reference_tests/README.md', 'sealed/reference_tests/test_interpreter_reference.py', 'sealed/reference_tests/test_learner_view.py']
unexpected_changes=[] missing_expected_changes=[]
```

## Learner-view audit

```bash
PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
from pathlib import Path
import importlib.util
import tempfile

root = Path('.').resolve()
module_path = root / 'sealed' / 'production' / 'learner_view.py'
spec = importlib.util.spec_from_file_location('learner_view_audit', module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='.validation-view-',
                                 dir=root / 'sealed' / 'production') as parent:
    destination = Path(parent) / 'view'
    entries = module.materialize(root, destination)
    audited = module.audit_view(destination)
    files = [entry for entry in entries if not entry.is_directory]
    mismatches = [str(entry.relative) for entry in files
                  if (root / entry.relative).read_bytes() !=
                  (destination / entry.relative).read_bytes()]
    bad_modes = []
    for entry in entries:
        mode = (destination / entry.relative).stat().st_mode & 0o777
        expected = 0o755 if entry.is_directory else 0o644
        if mode != expected:
            bad_modes.append(f'{entry.relative}:{mode:o}')
    readme = (destination / 'README.md').read_text(encoding='utf-8')
    print(f'learner_view_files={len(files)} audited_entries={len(audited)} byte_mismatches={mismatches} bad_modes={bad_modes}')
    print('learner_top_level=' + ','.join(sorted(path.name for path in destination.iterdir())))
    print(f'sealed_exists={(destination / "sealed").exists()} provenance_pointer={"PROVENANCE.json" in readme} license_pointer={"LICENSE_BOUNDARY.md" in readme}')
    print(f'license_summary={"CC0-1.0 catalog snapshot" in readme and "`NOASSERTION`" in readme and "does not assert a license for, or grant rights" in readme}')
    print(f'supplemental_absent={all(not (destination / name).exists() for name in module.INSTRUCTOR_TOP_LEVEL)}')
PY
```

Observed, exit 0:

```text
learner_view_files=20 audited_entries=24 byte_mismatches=[] bad_modes=[]
learner_top_level=AGENTS.md,CONCEPTS.md,DESIGN_QUESTIONS.md,MANIFEST.yaml,README.md,REQUIREMENTS.md,environment,public_tests,starter
sealed_exists=False provenance_pointer=False license_pointer=False
license_summary=True
supplemental_absent=True
```

The temporary learner view was created beneath the non-exported `sealed/production/` root and removed by
`TemporaryDirectory` after the audit.

## Limitations and label boundary

No network or upstream repository was accessed, so source, commit, catalog, and linked-resource license
assertions were not externally revalidated. No fuzzing, benchmark run, profiler, security assessment,
performance claim, transfer validation, or production validation was performed. Java availability does
not validate the Python implementation. The intentionally incomplete starter is not a completed solution.
Only an orchestrator-controlled independent validator may promote this artifact beyond `GENERATED` +
`PARTIAL`.
