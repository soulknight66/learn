# Independent validation log

All commands were bounded and read-only with respect to `CANDIDATE/`. Unless stated otherwise,
they ran from `CANDIDATE/` with `PYTHONDONTWRITEBYTECODE=1`. The candidate was not repaired and
neither attempted report command created its requested output.

## Toolchain

```text
$ command -v python3; python3 --version
/usr/bin/python3
Python 3.6.8

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5

$ command -v rg; command -v git
no output; both unavailable
```

Using the default interpreter, each of `environment/check_python.py`,
`environment/check_boundaries.py`, and `environment/check_starter.py` exited 1 at line 1:

```text
SyntaxError: future feature annotations is not defined
```

The substantive Python checks therefore used the explicit 3.11.5 executable shown above.

## Inventory, boundary, and static checks

```sh
for path in CANDIDATE/README.md CANDIDATE/REQUIREMENTS.md \
  CANDIDATE/GRAMMAR.md CANDIDATE/BYTECODE.md CANDIDATE/CONCEPTS.md \
  CANDIDATE/DESIGN_QUESTIONS.md CANDIDATE/starter CANDIDATE/public_tests \
  CANDIDATE/alternatives/treewalk; do
    test -e "$path" && echo "PRESENT $path" || echo "MISSING $path"
done
```

Observed:

```text
PRESENT CANDIDATE/README.md
PRESENT CANDIDATE/REQUIREMENTS.md
MISSING CANDIDATE/GRAMMAR.md
MISSING CANDIDATE/BYTECODE.md
PRESENT CANDIDATE/CONCEPTS.md
PRESENT CANDIDATE/DESIGN_QUESTIONS.md
PRESENT CANDIDATE/starter
PRESENT CANDIDATE/public_tests
MISSING CANDIDATE/alternatives/treewalk
```

```sh
PYTHONDONTWRITEBYTECODE=1 timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/check_python.py
PYTHONDONTWRITEBYTECODE=1 timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/check_boundaries.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/check_starter.py
```

Observed: all exited 0, respectively reporting:

```text
compiled 48 Python sources
learner-visible starter and public tests omit withheld paths and answer markers
starter is importable and intentionally incomplete
```

The boundary pass is narrow: its source does not require the missing learner documents.

```sh
grep -RInE '\beval[[:space:]]*\(|\bexec[[:space:]]*\(|shell[[:space:]]*=' \
  CANDIDATE --include='*.py'
find CANDIDATE -type l -print
find CANDIDATE -maxdepth 2 -type f \
  \( -iname 'license*' -o -iname 'copying*' -o -iname 'notice*' \) -print
```

Observed: no matches, no symlinks, and no license/notice file. `MANIFEST.yaml`,
`PROVENANCE.json`, and `benchmarks/results/smoke.json` all parsed successfully as JSON. The final
candidate inventory contained 64 files; no `__pycache__`, `.pyc`, or reviewer output was found.
Its final content digest (sorted per-file SHA-256 lines hashed again) was:

```text
7be98b46cb732aaf38f3aa52f53aa37bf0ac21d9af4c40e9b3c49ab46e0e0c0f
```

## Submitted test suites, executed independently

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference timeout 30s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference timeout 30s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/reference_tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference timeout 30s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/bytecode_tests -v
```

Observed:

| Suite | Result | Count | Elapsed reported |
| --- | --- | ---: | ---: |
| public | `OK`, exit 0 | 6 | 0.002 s |
| withheld contract | `OK`, exit 0 | 10 | 0.003 s |
| bytecode | `OK`, exit 0 | 5 | 0.001 s |

These are observed executions of builder-authored tests, not by themselves proof of any
validation label.

## Differential, benchmark, and exercise commands

```sh
PYTHONDONTWRITEBYTECODE=1 timeout 45s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  adversarial/grammar_fuzz.py --seed 7401 --iterations 3 --output reports/reviewer.json
```

Observed: exit 1; `alternatives/treewalk` child raised
`ModuleNotFoundError: No module named 'tinyvm'`. `reports/reviewer.json` did not exist afterward.

```sh
PYTHONDONTWRITEBYTECODE=1 timeout 45s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  benchmarks/benchmark.py --samples 3 --output benchmarks/results/reviewer.json
```

Observed: exit 1; the tree-walk worker raised the same `ModuleNotFoundError`.
`benchmarks/results/reviewer.json` did not exist afterward.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  debugging/parser-associativity/sealed/check_integrity.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=debugging/parser-associativity/buggy timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  debugging/parser-associativity/regression.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=debugging/parser-associativity/sealed/fixed timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  debugging/parser-associativity/regression.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  review_exercises/constant-folding/sealed/demonstrate.py
```

Observed, in order:

```text
isolated mutation and repair patch are structurally consistent                 (exit 0)
subtraction grouped incorrectly: wanted 12, observed (18,)                     (exit 1, intended buggy case)
subtraction is left-associative: (20 - 5) - 3 == 12                            (exit 0)
proposed optimizer eagerly evaluates an unreachable RHS and changes valid-program behavior (exit 0)
```

## Reviewer-authored semantic oracle

From the workspace root, a bounded inline Python program used `random.Random(20260831)` to
generate 300 fully parenthesized expressions of depth at most 3. It independently implemented
truncation-toward-zero division/remainder and expected values for `+ - * / % < <= > >= == !=
&& ||`, unary `-`/`!`, and injected unreachable division-by-zero right operands for short
circuit. It joined the cases as `print` statements, ran the reference once with
`max_steps=10000`, and asserted exact tuple equality.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=CANDIDATE/sealed/reference timeout 30s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
import hashlib
import random
import tinyvm

rng = random.Random(20260831)
ops = ('+', '-', '*', '/', '%', '<', '<=', '>', '>=', '==', '!=', '&&', '||')

def div(a, b):
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q

def expr(depth):
    if depth == 0 or rng.random() < 0.28:
        value = rng.randint(-9, 9)
        return (str(value) if value >= 0 else '-%d' % -value), value
    if rng.random() < 0.17:
        source, value = expr(depth - 1)
        if rng.randrange(2):
            return '(-(%s))' % source, -value
        return '(!(%s))' % source, int(value == 0)
    left_source, left = expr(depth - 1)
    right_source, right = expr(depth - 1)
    op = rng.choice(ops)
    if op == '&&' and left == 0 and rng.random() < 0.35:
        right_source, right = '(1 / 0)', 0
    elif op == '||' and left != 0 and rng.random() < 0.35:
        right_source, right = '(1 / 0)', 0
    elif op in ('/', '%') and right == 0:
        right_source, right = '1', 1
    if op == '+': value = left + right
    elif op == '-': value = left - right
    elif op == '*': value = left * right
    elif op == '/': value = div(left, right)
    elif op == '%': value = left - div(left, right) * right
    elif op == '<': value = int(left < right)
    elif op == '<=': value = int(left <= right)
    elif op == '>': value = int(left > right)
    elif op == '>=': value = int(left >= right)
    elif op == '==': value = int(left == right)
    elif op == '!=': value = int(left != right)
    elif op == '&&': value = int(left != 0 and right != 0)
    else: value = int(left != 0 or right != 0)
    return '(%s %s %s)' % (left_source, op, right_source), value

cases = [expr(3) for _ in range(300)]
source = ''.join('print %s;' % item[0] for item in cases)
expected = tuple(item[1] for item in cases)
actual = tinyvm.run_source(source, max_steps=10000).outputs
assert actual == expected
digest = hashlib.sha256(repr(actual).encode('ascii')).hexdigest()
print('reviewer_expression_oracle cases=300 seed=20260831 sha256=' + digest)
PY
```

Observed exit 0:

```text
reviewer_expression_oracle cases=300 seed=20260831 sha256=d2aef60bee02da13bd0344658075645897cdd576d738b2bcc37d3e61ae013ef3
```

This is positive evidence for the bytecode expression semantics tested, not full-language fuzz
coverage and not evidence for the missing tree-walk engine.

## Reviewer-authored resource and diagnostic probes

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=CANDIDATE/sealed/reference timeout 20s \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
import tinyvm
cases = {
    'unary_depth_1200': 'print ' + '!' * 1200 + '0;',
    'left_assoc_1200': 'print ' + '+'.join(['1'] * 1200) + ';',
    'paren_depth_1200': 'print ' + '(' * 1200 + '1' + ')' * 1200 + ';',
}
for name, source in cases.items():
    try:
        tinyvm.run_source(source, max_steps=10000)
    except BaseException as error:
        print(name, type(error).__name__, isinstance(error, tinyvm.LanguageError), str(error))
PY
```

Observed exit 0 from the probe itself, with all three API calls failing outside the typed error
hierarchy:

```text
unary_depth_1200 RecursionError False maximum recursion depth exceeded
left_assoc_1200 RecursionError False maximum recursion depth exceeded while calling a Python object
paren_depth_1200 RecursionError False maximum recursion depth exceeded
```

A second inline probe ran three faulting programs and inspected dataclass fields. Observed:

```text
'print missing;' RuntimeFault 'undefined variable: missing'
'print 1 / 0;' RuntimeFault 'division by zero'
'let x = 1; let x = 2;' RuntimeFault 'duplicate variable: x'
Binary_fields ['left', 'operator', 'right']
Instruction_fields ['opcode', 'operand']
```

This confirms that token locations do not survive into these AST nodes, instructions, or
runtime diagnostics.

## Historical benchmark artifact audit

A reviewer script recomputed sample count, median, minimum, maximum, positivity, and the
SHA-256 of expected output `(7260,)` for each result in `benchmarks/results/smoke.json`; every
internal check passed, and the two recorded PIDs differ. Key-presence checks observed:

```text
artifact_validation_label_present False
artifact_timestamp_present False
artifact_input_hash_present False
```

The timing values were not rerun or accepted as current benchmark evidence because the
tree-walk input implementation is absent.

## Limitations

- Network and the provenance source checkout were outside the permitted review environment, so
  the external article, catalog commit, license assertion, and no-copy claim were not compared.
- The missing tree-walk engine made semantic-step parity, full differential fuzzing, and current
  two-engine performance measurement inconclusive.
- `git` and `rg` were unavailable; `find`, `grep`, `diff`, direct Python parsing, and hashes were
  used as deterministic fallbacks.
