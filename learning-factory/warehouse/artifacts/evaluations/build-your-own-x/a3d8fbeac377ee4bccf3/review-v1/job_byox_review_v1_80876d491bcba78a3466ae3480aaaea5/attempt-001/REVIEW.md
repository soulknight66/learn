# Independent review

Verdict: **REVISE**. The submission is candidly labeled `GENERATED + PARTIAL`,
and that label should remain. Its educational design is promising, but native
correctness is unverified and the supplied execution harnesses do not meet the
repository's containment invariants.

## Prioritized findings

### P1 — Harness containment is incomplete

The executable under test is learner-supplied code, so its timeout boundary must
be enforced by the worker harness. The calls in
`public_tests/run_tests.py:33-40`,
`sealed/reference_tests/run_reference_tests.py:33-40,123-130,136-143`, and
`sealed/benchmarks/benchmark_driver.py:41-47` use argv arrays, capture output,
and set a timeout, but they do not create and terminate a process group. On a
timeout, descendants can survive the directly killed process. In addition,
`environment/check.sh:13` runs `make` without any deadline.

Both test suites create source files with `open(..., "w")` and never make them
read-only (`public_tests/run_tests.py:25-28` and
`sealed/reference_tests/run_reference_tests.py:25-28`), contrary to the
submitted working agreement at `AGENTS.md:16-17`. A tested executable running as
the same user can alter its fixture.

Use a worker-controlled subprocess wrapper with a new process group, an overall
deadline, group termination and reaping, bounded captured logs, and an explicit
per-attempt scratch directory. Materialize inputs as read-only and add
deterministic tests for timeout and descendant cleanup. Builder-owned scripts
must not be used to promote validation labels by themselves.

### P1 — There is still no native correctness evidence

Neither `fpc` nor `ppcx64` is available. The submitted environment check
correctly returned `PARTIAL`, while both Python suites stopped in `setUpClass`
and reported `Ran 0 tests`. `make -n` only confirmed the intended command; it did
not compile Pascal.

Static review found a coherent lexer/parser/VM design, but cannot establish that
the Pascal compiles or that its exact runtime and formatting behavior matches the
contract. A worker-controlled validator still needs to copy build inputs into
scratch space, compile the starter scaffold and sealed reference with a recorded
Free Pascal 3.2.x toolchain, then run the 12 public and 17 sealed tests with full
logs. The adversarial seeds should be executed separately. Until then, do not
claim `BUILDS` or `TESTED`.

### P2 — One public acceptance assertion is materially incomplete

`public_tests/run_tests.py:96-99` checks that addition overflow writes a runtime
diagnostic prefix, but does not require exit status 70 or empty stdout. A program
can fail this part of the command-line contract and still pass that method. Add
the same return-code and output assertions used by the other runtime-error tests.
This matters to learners because the public suite is presented as their primary
feedback loop.

### P2 — Generated-material reuse rights are unspecified

The license boundary is commendably conservative: catalog metadata is identified
as CC0, the linked article stays `NOASSERTION`, and no rights to the linked work
are claimed. However, `LICENSE_BOUNDARY.md:11-13` and
`PROVENANCE.json:3-8` only describe the new material as independently generated
for personal educational use. That is not a license grant, and there is no
`LICENSE`/`COPYING` file for the generated Pascal, tests, or prose.

Before distributing the pack, state the generated material's actual terms with
an SPDX identifier or an explicit all-rights-reserved/internal-use policy. Do not
apply the catalog's CC0 waiver to the generated files or to the linked resource.

### P2 — Exact reconstruction of the generated artifact is not documented

Source catalog provenance is internally consistent and includes a commit, tree
hash, extractor version, and snapshot digest. It does not identify the generation
tool/model/version or invocation, and the manifest has no canonical digest for
the complete generated tree. The environment specifies the range “Free Pascal
3.2.x” rather than a captured compiler identity. The byte hashes in the submitted
validation cover only `MANIFEST.yaml` and `PROVENANCE.json`.

Record a canonical artifact-tree digest and generation job/tool identity, and
retain the exact compiler version, flags, platform, executable digest, and test
logs when native validation becomes available. This would make provenance about
the generated result, not only its catalog input.

### P2 — Disclosure layout is clean, but enforcement is not evidenced here

Manual inspection found solution-bearing reference code, answers, adversarial
seeds, deeper tests, and production analysis under the root `sealed/` directory;
no symlink or obvious answer copy escapes that tree. The learner-facing material
uses staged requirements, concepts, debug modes, prompts, and TODO scaffolding
without presenting the reference implementation.

The reviewer bundle necessarily makes `sealed/` readable, however, and no
machine-readable view allowlist or worker-controlled transfer report accompanies
it. A directory name and instructions not to read it are not proof of isolation.
Before learner delivery, materialize and inspect the actual student view and
record that no sealed path or content is present. The submission appropriately
does not claim `TRANSFER_VERIFIED`.

## Other observations

- The normative language specification is unusually precise about token
  locations, name visibility, arithmetic, output persistence, instruction count,
  diagnostics, and exit statuses.
- The starter separates types, CLI, lexer, compiler, and VM, while token and
  bytecode modes provide useful incremental debugging surfaces.
- Static inspection of the reference found precedence and associativity loops,
  declaration ordering, flat slot allocation, jump patching, right-before-left
  popping, explicit arithmetic-domain checks, and pre-dispatch step counting
  aligned with the prose. This is review evidence only, not a native result.
- The author is honest about residual denial-of-service and production risks:
  recursion depth, source size, repeated dynamic-array growth, linear name lookup,
  unexpected exceptions, and output quotas remain unresolved. `productionized:
  false` is correct.
- The benchmark, fuzz/adversarial, review, and production documents avoid
  promoting the mere presence of scripts or prose into validation labels.

## Acceptance conditions

At minimum: harden the worker execution boundary, complete independent native
build/test validation, correct the public overflow assertion, define generated
material licensing, and validate the materialized learner view. Preserve all
failed attempts and logs, and keep the manifest at `PARTIAL` unless a
harness-controlled validator authorizes a transition.
