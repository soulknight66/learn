# Independent review

Verdict: **REVISE**. The repaired reference is technically strong and its recorded validation claims reproduced, but the submitted pack still needs a verifiable learner-view boundary and two learner-facing documentation clarifications.

## Prioritized findings

### P1 — Progressive disclosure is conventional, not proven

`AGENTS.md:3-4` and `README.md:20` tell learners not to inspect directories named `sealed`, but the same submitted tree contains readable reference source, hidden-side tests, design answers, and exercise answers. `environment/README.md:12-17` also publishes the command that executes the sealed test files. The pack audit verifies where files are located; it does not construct or validate the student projection.

Prose and directory names are useful classification, but are not access control. Before publishing, the deterministic harness should produce and validate a learner view that excludes every path whose component is `sealed` (including nested exercise answers), plus instructor-only reference and hidden-test artifacts. If that projection already exists outside this workspace, capture its file inventory or acceptance result as evidence; this finding then becomes externally satisfied.

### P2 — The advertised CLI examples are not reproducible

`README.md:30-34` invokes `examples.mica`, but that file is absent. Replaying the documented tree command exited `1` with:

```text
ENOENT: ENOENT: no such file or directory, open 'examples.mica'
```

Add a small non-solution sample program, or clearly mark the filename as learner-supplied and show a stdin example. This is separate from the public suite's intentional TODO failures, which are accurately disclosed.

### P2 — Unicode position units are underspecified

`REQUIREMENTS.md:20` declares Unicode source and `REQUIREMENTS.md:38-40` defines offsets and columns, but does not say whether those values count UTF-16 code units, Unicode code points, or grapheme clusters. The supplied lexer indexes JavaScript strings and therefore counts UTF-16 units: in `"😀"; print 1;`, `PRINT` starts at offset `6`, column `7`, while code-point counting would produce column `6`.

State the required unit explicitly, including CR/LF handling. Otherwise a reasonable learner implementation can disagree with the supplied reference and hidden diagnostics while still following the prose.

### P3 — Redistribution remains intentionally unlicensed

`LICENSE_BOUNDARY.md:3-14` correctly distinguishes CC0 catalog metadata from the linked resource's `NOASSERTION` status and honestly says redistributors must make their own license decision. The generated pack itself has no affirmative redistribution license. This is not a misleading claim, but it prevents safe transfer or publication until an owner selects and records a license.

## Evidence that passed

- The exact configured Node binary reported `v22.21.0`, and every submitted `.mjs` file passed syntax checking.
- Independent runs passed 13/13 reference tests and 6/6 adversarial tests.
- A separate 514-execution oracle matrix passed across both backends.
- Input non-mutation checks passed; accessor, inherited-field, sparse-array, malformed-span, hostile-opcode, underflow, jump, and scope guards behaved deterministically in the bounded probes.
- Tree and VM CLI smoke runs both printed `8`.
- The untouched public baseline produced the disclosed result: lexer suite pass, parser and execution suite failures at TODO stages.
- The pack audit passed with 57 files scanned and no detected forbidden path, symlink/special file, or credential pattern. Imports were Node built-ins or relative modules; the static forbidden-API scan found no match.
- Manifest/provenance identifiers agree internally. Labels remain only `GENERATED` and `PARTIAL`; `productionized` is false. The prose does not claim BUILDS, TESTED, FUZZED, BENCHMARKED, REVIEWED, TRANSFER_VERIFIED, or PRODUCTIONIZED.

## Review limits

The upstream snapshot and linked repository were unavailable, so provenance hashes, upstream licensing, and the no-copy statement could not be independently compared to source material. Only Node.js `v22.21.0` was exercised. The tests and matrix are bounded correctness evidence, not fuzzing, formal verification, security certification, benchmark qualification, cross-runtime validation, transfer verification, or production evidence.

This verdict is advisory and does not award `REVIEWED`; only the orchestrator-controlled acceptance validator may publish that label.
