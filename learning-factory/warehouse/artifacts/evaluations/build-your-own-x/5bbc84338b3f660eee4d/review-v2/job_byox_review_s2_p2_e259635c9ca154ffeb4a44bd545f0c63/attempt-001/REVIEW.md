# Independent review

Advisory verdict: **REVISE**  
Builder job: `job_byox_build_s2_8949bd3a7c89916f517bc30e41b57243`  
Project: `project_d49f1492abb05519b3c18d8a793d37a2`

The pack has a clear normative specification, useful conceptual sequencing, intentionally incomplete starter code, broad reference tests, explicit production caveats, and unusually honest validation labels. Those strengths do not overcome the following acceptance-blocking issues.

## Prioritized findings

### High — valid arbitrary-precision input escapes as a host exception

`REQUIREMENTS.md` requires arbitrary-precision integers and says raw host exceptions must not cross the interpreter API. The reference reader passes every integer token directly to `int()` at `sealed/reference/pebble/reader.py:150`. Under the required Python 3.11 runtime, `read_one("9" * 5000)` raises raw `ValueError` because Python limits decimal conversion to 4,300 digits by default.

This also breaks the CLI contract: the same valid expression exits 1, prints a traceback, and lacks the required `error:` prefix instead of returning status 2. A valid source nested 1,100 lists deep similarly raises raw `RecursionError`. The latter risk is candidly disclosed in `sealed/REVIEW.md`, but the claim there that the reference satisfies the written contract is too broad.

Required revision: either implement the stated unbounded integer conversion/printing contract or define a deterministic source limit in the normative requirements. Convert all accepted-input/resource failures into stable Pebble errors and add API plus CLI regression tests for both integer size and nesting boundaries.

### High — progressive disclosure is stated but not enforced

The submitted learner-adjacent tree includes the full implementation in `sealed/reference/`, all sealed tests, design/review material, and exercise answers at predictable paths. Direct inspection confirmed that the starter, reference implementation, and sealed answer files are all readable with the same file mode. `AGENTS.md` saying not to inspect them is guidance, not isolation, and neither the manifest nor another submitted artifact defines a deterministic learner-view export/filter.

If a learner receives `CANDIDATE/` as submitted, the complete solution and hidden expectations are immediately available. This defeats the proposed reveal order and prevents the sealed suite from functioning as hidden evidence.

Required revision: materialize and test a learner view that excludes every sealed/reference/answer path, and retain those files only in a harness-controlled validator view. Record that view construction and its path audit as deterministic evidence.

### High — the primary learner commands select an incompatible interpreter

`README.md`, `AGENTS.md`, and `public_tests/README.md` tell learners to run `python3`. In this provided environment that command is Python 3.6.8, while `environment/README.md` correctly says the pack requires Python 3.11+. The documented public command consequently fails on PEP 604 type annotations and on `subprocess.run(text=...)` before it can meaningfully test learner work.

The configured absolute Python 3.11.5 binary works. The public suite then needs a writable temp location in this immutable review workspace; with `TMPDIR=..`, all 19 tests pass against the reference.

Required revision: use the configured absolute interpreter, or a verified launcher variable, in every copy-paste command. Add an early version check and document a writable temporary-directory requirement for restricted workspaces.

### Medium — conditional jump validation depends on branch selection

`sealed/DESIGN.md:60-62` says the optional VM validates jump targets. In `sealed/reference/pebble/vm.py:49-52`, however, `JUMP_IF_FALSE` validates its target only when the condition is false. A program with a true constant and target `99` returned `42` rather than rejecting malformed bytecode.

Required revision: validate every jump operand before considering its condition, and test valid/invalid targets with both truth values. If only executed targets are meant to be checked, narrow the design claim explicitly.

### Low — the tail-position review exercise has unrelated unacknowledged defects

`review_exercises/tail_position/candidate.py:6` delegates branch selection to Python truthiness, always indexes an else branch, and `:11` indexes an empty `do`. These violate the same normative contract the exercise asks the learner to review, but the sealed answer discusses only host recursion. This makes a careful learner's additional findings appear unsupported and overlaps the dedicated truthiness exercise.

Required revision: make the fragment otherwise contract-correct, or list the intentionally elided preconditions and cover all accepted findings in the sealed review.

## Evidence that held up

- Configured Python reported 3.11.5; configured Java reported Temurin 21.0.5+11 and is correctly described as unused.
- All 29 Python files passed an independent in-memory syntax check.
- The sealed suite independently reported 49/49 passing. The public suite reported 19/19 passing against the reference once a writable `TMPDIR` was provided. The CLI smoke printed `42`.
- The 6,000-call tail-recursion check, lexical closure checks, exact bool/int boundary checks, CLI error cases, artifact type checks, and credential-pattern audit passed as part of the rerun sealed suite.
- An independent AST audit found only standard-library/local imports and no direct builtin `eval`, `exec`, `compile`, or `shell=True` calls.
- Manifest/provenance project, source, and commit identifiers agree. Canonical manifest and provenance digests reproduce the values frozen by the structure suite.
- The license boundary carefully distinguishes the CC0 catalog from the linked resource's `NOASSERTION` status and does not claim copied linked content. The external origin assertion itself could not be independently compared because the immutable source snapshot was unavailable.
- The manifest remains `GENERATED` + `PARTIAL`, sets `productionized: false`, and does not claim any validation label that the builder's own scripts cannot establish.

## Scope limitations

No network or upstream material was accessed. The source snapshot needed to verify provenance and license assertions was not supplied. The submitted artifact does not show whether a separate orchestrator creates a filtered learner view. No fuzzing, benchmarking, transfer, security, or production validation was performed or inferred.

Only a separate orchestrator-captured acceptance validator may publish `REVIEWED`; this verdict does not promote the manifest.
