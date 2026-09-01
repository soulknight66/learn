# Independent review

Verdict: **REVISE**. The pack is unusually clear and candid, and most independently exercised behavior works. Three high-priority issues prevent acceptance as a correct, safely runnable learning artifact.

## Prioritized findings

### High — the value round-trip contract is internally unsatisfiable

`REQUIREMENTS.md:27-39` says symbols print as their unquoted names and every non-callable data value must survive printing and reading. `REQUIREMENTS.md:90-91` also requires `(type nil)` to return the symbol `nil`. Those requirements collide: `sealed/reference/sprig/runtime.py:224-242` creates `Symbol("nil")`, `printer.py:23-24` emits `nil`, and the reader necessarily restores the nil literal (`None`).

Independent witness on Python 3.6.8:

```text
value=Symbol('nil') rendered='nil' restored=None equal=False
```

This is not just a hostile host-API value; Sprig itself produces it. Learners cannot implement both requirements simultaneously. Define a canonical escaped-symbol spelling (including reserved, numeric, empty, whitespace, and delimiter-containing names), or narrow/change the round-trip and type-tag contracts. Add conformance cases for every type symbol and ambiguous symbol spelling.

### High — host decimal limits break documented integers and leak a traceback

`REQUIREMENTS.md:16-17` accepts every atom matching `[+-]?[0-9]+` as an integer, and `REQUIREMENTS.md:33,39` requires integers to print and round-trip. The available Python 3.6.8 and 3.11.5 runtimes both enforce a 4,300-digit conversion ceiling:

```text
digits=5000 language_error=READ_INTEGER
```

Worse, two individually accepted 3,000-digit operands can be multiplied into an integer that `printer.py:15` cannot render. The independent CLI probe observed exit 1, empty stdout, and a traceback ending in:

```text
ValueError: Exceeds the limit (4300) for integer string conversion
```

This contradicts the integer, printing, and CLI behavior on the stated generation host itself. Either implement host-limit-independent decimal parsing/rendering or specify a deterministic Sprig digit limit and stable language error. Test both oversized input and an oversized arithmetic result.

### High — CLI tests can hang on faulty learner code

`public_tests/test_05_cli.py:11` and `sealed/reference_tests/test_cli_reference.py:9` call `subprocess.run` with argv arrays and captured streams, but without a timeout or process-group isolation. A learner's infinite loop, blocked read, or spawned descendant can hang the documented suite indefinitely. That violates the repository rule requiring bounded subprocesses and process groups.

Use a shared Python-3.6-compatible subprocess helper with a deadline, a fresh process group/session, and full-group termination on timeout. Retain captured stdout/stderr and turn timeout into a deterministic test failure.

### Medium — generated-material reuse rights are unspecified

`LICENSE_BOUNDARY.md` correctly refuses to treat the catalog's CC0 status as permission for the linked resource, whose license is `NOASSERTION`. It describes the local files as independently generated for personal educational use, but neither that file nor a `LICENSE` grants rights in the generated code, tests, or prose. Add an explicit SPDX license/grant, or state that the artifact is intentionally internal/proprietary. The no-copy claim could not be compared with upstream in this environment.

## Validation and learner assessment

- With a writable workspace temporary directory, the reference passed all 24 public and 34 sealed tests on both Python 3.6.8 and 3.11.5.
- An independent deterministic matrix matched evaluator and VM behavior in 55 cases, and 24 malformed bytecode cases all produced `VM_*` language errors.
- The ordered milestones, stable APIs, design questions, intentional starter gaps, and supplemental debugging/review exercises are useful and progressively disclosed in the prose.
- Reference solutions and answers are consistently placed below directories named `sealed`. Actual learner isolation remains unproved because no materialized student view or transfer verification was supplied; filtering must be recursive so nested exercise answers are excluded too.
- Structure, provenance identity, strict JSON parsing, lack of symlinks/special files, standard-library-only imports, and absence of host `eval`/`exec` were independently corroborated.
- Validation claims are honest: the manifest remains `GENERATED` + `PARTIAL`, requires independent validation, and explicitly declines fuzzing, benchmarking, transfer, production, and independent-review claims. Builder-authored prose and its checker were not treated as proof on their own.

The exact public command failed only at its temporary-file test in this immutable review sandbox because no system temp directory was usable. Setting `TMPDIR=..` produced 24/24 passes without modifying `CANDIDATE/`; this environmental caveat is recorded in `VALIDATION.md`.
