# Independent review

Verdict: **REVISE**. The pack is candidly labeled and educationally promising, but the sealed
reference has correctness and trust-boundary defects, the advertised test layout is not explicit
enough for the supported Node range, and progressive disclosure has not been demonstrated. Nothing
in this review promotes a manifest validation label.

## Prioritized findings

### P1 — Bytecode validation can execute an inherited array method

`REQUIREMENTS.md:114-121` requires untrusted bytecode to be fully validated as data before dispatch
and requires invalid input to raise `BytecodeError`. `sealed/reference/src/vm.js:270-280` checks own
array keys and element descriptors but never checks the array prototype. The validator then calls
`program.code.at(-1)` at line 65.

A focused probe used an otherwise valid dense code array whose prototype supplied `at`. The inherited
method ran during validation (`atCalls=1`) and execution returned successfully. Giving the same dense
array a null prototype instead produced `TypeError: program.code.at is not a function`, with no
language stage. Thus the validator both invokes attacker-controlled behavior and leaks a host error
for an input that passes its dense-data checks. This is not the harder Proxy limitation already
acknowledged in `sealed/REVIEW.md`; ordinary array prototypes can be handled deterministically.

Revise the validator to avoid inherited methods and either require an approved array prototype or
copy validated own data into fresh harness-owned arrays before any semantic access. Add tests for
null prototypes, subclasses, custom inherited methods, and no side effects before rejection.

### P1 — Valid identifiers collide with `Object.prototype`

The identifier grammar at `REQUIREMENTS.md:15-18` permits `constructor`, `toString`,
`hasOwnProperty`, and `__proto__`. `sealed/reference/src/tokens.js:35-46` creates `KEYWORDS` as a
normal object, and `sealed/reference/src/lexer.js:135` uses `KEYWORDS[text] ?? T.IDENTIFIER` without
an own-property check.

The independent transformed probe observed a function-valued token type for the first three names
and an object-valued type for `__proto__`; none was `IDENTIFIER`. The valid program
`let constructor = 1; constructor;` then failed with `ParseError` at 1:5. Use a null-prototype keyword
table, `Map`, or an own-property check, and add every inherited-name case to lexer and end-to-end
tests.

### P1 — A valid flat expression makes the two engines disagree

The parser builds addition left-associatively without increasing parse depth for each operator. The
compiler recursively walks that left-deep AST (`sealed/reference/src/compiler.js:41-42,126-135`) and
enforces an undocumented, non-raisable maximum compile depth of 1,000. A 1,000-term addition is only
2,000 source characters and 2,000 non-EOF tokens; it is below all relevant stated limits, and its
tree evaluation uses about 2,000 visits.

The focused probe observed:

```text
1000 terms tree: value=1000
1000 terms vm: CompileError stage=compile message=Compile depth exceeds 1000 at 1:1
```

This conflicts with the every-valid-source parity promise at `REQUIREMENTS.md:123-124`. Compile
left-associative chains iteratively, state and align a source-level complexity limit for both engines,
or narrow the language contract. Add a regression at and around the boundary. Larger flat trees can
also exhaust a host call stack in the recursive tree walker before the documented 100,000-step limit,
so bounded iterative traversal deserves the same treatment.

### P1 — The documented test entry points lack an explicit module scope

Only `starter/package.json` and `sealed/reference/package.json` declare `"type": "module"`.
`public_tests/*.test.js`, `sealed/reference_tests/*.test.js`, and
`debugging/precedence/buggy-parser.test.js` are siblings, not descendants, of those package scopes,
yet all use ESM `import` syntax. On Node versions/configurations that treat ambiguous `.js` as
CommonJS—including the beginning of the declared Node 20 support line—the documented commands reject
the test entry files before assertions run.

Add a root/package-local `type=module` marker, rename external entries to `.mjs`, or document and test
an explicit runtime flag. Validate the exact commands on the oldest supported Node 20 release and a
current LTS. This review host had no Node, so it could not determine behavior on newer syntax-detecting
releases; that uncertainty is itself avoidable packaging ambiguity.

### P1 — Progressive disclosure relies only on a naming convention

The full submitted tree contains the complete reference implementation, design answer, debugging
answer, corrected parser, and bytecode-review answer under `sealed/`. Learner-facing imports did not
reference those paths, which is good, but neither a deterministic student-view allowlist nor an
executable isolation/transfer check is present. `environment/verify_artifact.py` confirms that sealed
content is not nested under a few learner directories; it does not construct or inspect the view a
learner actually receives.

Do not distribute the full tree as the student view. Have the worker harness create the view from an
explicit allowlist and independently assert that every sealed/reference/answer path and content hash
is absent. Keep transfer validation unclaimed until that harness-controlled check runs.

### P2 — Two learner-contract edges need an unambiguous decision

- `REQUIREMENTS.md:120-124` promises matching limits and exact engine outcomes, while the design uses
  AST visits versus dispatched instructions. The probe `print 1;` with `maxSteps: 2` succeeded in the
  tree engine but raised a VM `RuntimeError`. Either exclude budget-boundary outcomes from parity or
  define a shared source-level cost model.
- The formal grammar at line 50 permits only a bare `IDENTIFIER` before assignment, but the reference
  accepts `(a) = 1` because parentheses disappear and the remaining node is an `Identifier`. The probe
  parsed and executed `let a=0; (a)=1; a;` successfully. State whether grouped identifiers are valid
  assignment targets and align grammar, reference, and tests.

There is also a small wording error at `REQUIREMENTS.md:87`: “Unary `-`, `-`, `*`, `/`” should name
binary subtraction explicitly.

### P2 — Artifact regeneration and redistribution are not fully specified

The provenance records a catalog commit, tree hash, extractor version, and conservative license
boundary, but not the generator implementation/version, generation inputs, or a command capable of
recreating this 61-file artifact. The manifest's `provenance_sha256` matches the embedded snapshot
identifier, but the underlying snapshot was not supplied for recomputation.

The license text is appropriately honest: CC0 applies to catalog metadata, the linked resource is
`NOASSERTION`, and the generated material is described only as for personal educational use. That
description is not a redistribution license. If sharing or modification is intended, add an explicit
owner-approved license and SPDX/copyright information; otherwise state the restriction prominently.

## Strengths retained

- Manifest claims are conservative: `GENERATED` + `PARTIAL`, independent validation required, and
  `productionized: false`. The prose explicitly disclaims Node tests, fuzzing, benchmarks, transfer,
  and deployment.
- Requirements, concepts, design questions, staged starter files, narrow public tests, adversarial
  seeds, and exercises provide useful progressive learning material once the blockers above are fixed.
- The inspected learner source had no sealed imports, symlinks, dynamic evaluation, filesystem,
  network, subprocess, or environment-variable use. The scan is supportive static evidence, not a
  security or test label.

