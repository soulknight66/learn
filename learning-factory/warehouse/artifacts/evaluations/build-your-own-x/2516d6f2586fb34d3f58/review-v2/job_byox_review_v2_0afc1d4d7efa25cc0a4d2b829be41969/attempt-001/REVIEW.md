# Independent review

Verdict: **REVISE**. The bytecode reference has a sound core and useful exercises, but the
submitted pack is missing required learner specifications and its advertised second engine.
Those omissions break the documented learning path and make the supplied differential and
benchmark workflows unreproducible. No validation target should be promoted from this review.

`CANDIDATE/` was treated as immutable; neither its manifest nor its artifacts were repaired.

## Prioritized findings

### Blocker — the learner-visible language and bytecode specifications are absent

`README.md:11` tells learners to begin with `GRAMMAR.md` and `BYTECODE.md`, and lines 20–22
describe a view containing six learner documents. Neither file exists, leaving only four
top-level learner documents. The starter parser asks for a “documented precedence ladder,” and
the compiler asks learners to emit instructions, but there is no complete grammar, opcode
contract, stack effect table, jump convention, or bytecode validation contract to implement.

The boundary checker still exits 0 because it scans those paths only when they exist; it never
requires them. Add both specifications and make the learner-view validation fail when any of
the six documents is missing. Include deterministic tests that build the actual exported
learner view, not just substring checks over selected files.

### Blocker — the declared tree-walk architecture was not submitted

`MANIFEST.yaml:8-12`, `REQUIREMENTS.md:5-7`, the progressive path, the fuzz harness, and the
benchmark all declare `alternatives/treewalk`. That directory is absent. Consequently:

- `adversarial/grammar_fuzz.py --seed 7401 --iterations 3 ...` exits 1 when the tree-walk child
  cannot import `tinyvm`.
- `benchmarks/benchmark.py --samples 3 ...` exits 1 for the same reason.
- Equal semantic step boundaries, differential agreement, and the architecture comparison are
  uncheckable.
- `benchmarks/results/smoke.json` reports a tree-walk run produced by code that is not in the
  submitted artifact.

Submit the exact tree-walk implementation used to generate evidence, then rerun independent
validation. If the second architecture is intentionally removed, remove every associated
contract and historical result rather than leaving an internally inconsistent vertical.

### Major — modest valid inputs escape through host `RecursionError`

Reviewer probes using 1,200 unary operators, 1,200 nested parentheses, and 1,200
left-associated additions each escaped `run_source` as `RecursionError`, not as a
`LanguageError`. The last case is only about 2.4 KiB and reaches compiler recursion even though
the parser builds it iteratively. `max_steps` meters execution only, so it does not bound this
parse/compile work.

This contradicts the pack's bounded-resource and typed-failure framing. Define deterministic
source/token/nesting/AST/instruction limits, enforce them before host recursion is exhausted,
and expose a typed `ParseError`, `CompileError`, or `ResourceLimit`. Add boundary tests on both
sides of each limit and run them with a fixed supported Python version.

### Major — advertised source locations stop at tokens

`README.md:5-7` presents source locations as one of the exercise's contracts. Tokens have line
and column fields, but AST `Binary` nodes contain only `left`, `operator`, and `right`, while
instructions contain only `opcode` and `operand`. Observed runtime messages were simply
`undefined variable: missing`, `division by zero`, and `duplicate variable: x`; none identifies
the source site. The withheld location test checks only a lexer error, so it does not cover the
loss across parsing and compilation.

Carry spans through AST and bytecode nodes and assert locations for parse, compile, and runtime
failures. If only lexical diagnostics are intended, narrow the README promise explicitly.

### Major — the historical benchmark is not attributable validation evidence

The smoke JSON's sample counts, medians, extrema, positive timings, output hashes, and distinct
PIDs are internally consistent. It also records the interpreter and candidly limits its
interpretation. However, it cannot be regenerated from this submission because the measured
tree-walk code is absent. It also lacks an explicit validation label, generation timestamp, and
content hash tying both implementations and the workload to the report.

Treat the current JSON as unverified historical data, not evidence of `BENCHMARKED`. After
restoring the implementation, record immutable input hashes, timestamp, validator identity and
result, and retain the raw command/environment fields already present.

### Major — provenance boundaries are candid, but the generated pack has no license

`PROVENANCE.json` usefully says that CC0 applies only to catalog metadata, labels the linked
article `NOASSERTION`, identifies all pack content as agent-generated, and says linked content
was not copied. No `LICENSE`, `COPYING`, or `NOTICE` file exists, though, and “for personal
educational use” is not a standard license grant. Learners therefore cannot determine whether
they may copy, modify, or redistribute the generated code and exercises.

Add an explicit license for the generated pack and keep the current catalog/article boundary.
The external no-copy assertion remains inconclusive here because the restricted review
environment could not access the catalog checkout or article.

### Moderate — the runtime prerequisite and test commands are not reproducible for learners

The shell's default `python3` is 3.6.8; every environment script fails immediately on the
annotations future import. The code also uses syntax requiring a newer Python. Python 3.11.5
works, but only the historical benchmark embeds that absolute interpreter path. The learner
documents specify neither a minimum Python version nor exact `PYTHONPATH`/`unittest` commands.

Declare and check a supported Python range (or provide a locked environment) and give copyable
commands for starter, public, reference, and exercise workflows. A compatibility check should
emit a deliberate version diagnostic instead of failing at parse time.

### Moderate — “one stage at a time” lacks stage-level feedback

The TODO markers cleanly separate lexer, parser, compiler, and VM work, and the starter does not
leak the sealed solution. But all six public tests call the final `run_source` API, so an early
learner receives only `NotImplementedError` until several layers exist. After restoring the
specifications, add public milestone tests for tokens/locations, AST shape and precedence,
straight-line bytecode/stack effects, and VM execution before full control flow.

## Correctness evidence that did hold

- With explicit Python 3.11.5, the bytecode reference passed 6 public, 10 withheld-contract,
  and 5 bytecode tests in independent execution.
- A reviewer-authored deterministic oracle matched 300 generated expression programs across
  arithmetic, truncating division/remainder, comparisons, boolean normalization, unary
  operators, and short circuit. Seed: `20260831`; output digest:
  `d2aef60bee02da13bd0344658075645897cdd576d738b2bcc37d3e61ae013ef3`.
- The bytecode verifier rejected the submitted malformed cases, and no Python `eval`, `exec`,
  or `shell=True` engine pattern was found.
- The parser-associativity integrity check passed; the buggy regression produced `(18,)`, the
  fixed regression produced `12`, and the constant-folding counterexample reproduced.
- The manifest is appropriately conservative: it says `GENERATED_CANDIDATE`,
  `NOT_PRODUCTION_READY`, and `productionized: false`. Its `validation_targets` are targets,
  not completed validation labels.

These results support only the present bytecode paths and the stated cases. Submitted tests and
scripts are not self-authenticating evidence, and the independent checks do not compensate for
missing deliverables.

## Validation-target assessment

| Target | Independent assessment |
| --- | --- |
| `BUILDS` | Partial bytecode syntax/import evidence under Python 3.11.5; not established for the declared two-engine artifact. |
| `TESTED` | Bytecode paths have passing bounded evidence; cross-architecture and depth/resource contracts do not. |
| `FUZZED` | Not established. The full harness cannot run; the reviewer oracle covered expressions only. |
| `BENCHMARKED` | Not established. The historical JSON is internally consistent but not reproducible or attributable to the submitted inputs. |
| `REVIEWED` | This independent review was completed, but it does not promote the candidate or erase its blockers. |
| `TRANSFER_VERIFIED` | No transfer evidence was supplied or observed. |
| `PRODUCTIONIZED` | Correctly disclaimed by the manifest. |

