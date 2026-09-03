# Independent review

Verdict: **PASS (advisory)**. No P0, P1, or P2 correctness, honesty, isolation-layout, or learner-usability defect was found. This report does not edit the candidate manifest and cannot publish a `REVIEWED` label.

## Prioritized findings

1. **P3 — redistribution rights remain intentionally unresolved.** `LICENSE_BOUNDARY.md` clearly limits the generated material to personal educational use and grants no public redistribution license. This is honest and does not block the reviewed use, but authorization is required before publication or redistribution.
2. **P3 — final progressive-disclosure enforcement is external.** Answers, the reference, and adversarial tests are consistently segregated under validator-only paths, and no forbidden answer/reference directory occurs beneath `starter/`, `public_tests/`, or `environment/`. The full reviewer submission necessarily contains `sealed/`; an actual student-view export was not available to prove those files are excluded at delivery time.
3. **P3 — some validation boundaries remain open.** LeakSanitizer is unusable under ptrace here, the external content-addressed inventory and immutable source snapshot were absent, and no fuzzing, cross-architecture execution, transfer validation, or production assessment was performed.

## Correctness and reproducibility

The reference and starter both compile cleanly with strict GCC 15.2.0 flags. The reference also builds with the advertised system GCC 8.5.0. Independent executions observed 13/13 reference tests, 6/6 public tests, and 7/7 adversarial tests passing; the reference suite also passed under Python 3.6.8.

A reviewer-authored deterministic oracle checked 80 generated signed-64-bit expressions through both `eval` and compile/link/native execution. It also checked 11 exact boundaries for nesting, AST depth, variables, duplicate-resolution precedence, and fuel, plus two hostile process-runner cases. All passed. ASan/UBSan runs repeated the supplied reference suite and the independent arithmetic/boundary cases without diagnostics when leak detection was disabled.

Two compilations of the same Pebble input emitted byte-identical assembly. Metadata is strict JSON despite the manifest suffix; identifiers and logical provenance digest agree across files; the recorded manifest/provenance byte hashes were reproduced.

## Learner value and validation honesty

The challenge has a precise observable contract, a useful lexer-first milestone, conceptual guidance, design prompts, disclosed public tests, and strong warnings about the limits of smoke testing. The starter is deliberately incomplete and fails its public/lexer checks as documented; it is not presented as a finished solution.

Claim discipline is good: the manifest remains `GENERATED` + `PARTIAL`, independent validation is required, and `productionized` is false. The single benchmark smoke is self-checking but establishes no performance threshold and is not treated as `BENCHMARKED`. Nothing in this review establishes `FUZZED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.

## License and provenance

The internal boundary is coherent: catalog metadata is identified as CC0-1.0, linked content is marked `NOASSERTION`, the upstream link is treated as provenance only, and generated content is separately classified. With no source snapshot or network access, the upstream commit/license and no-copy assertions remain uncorroborated rather than accepted as facts.
