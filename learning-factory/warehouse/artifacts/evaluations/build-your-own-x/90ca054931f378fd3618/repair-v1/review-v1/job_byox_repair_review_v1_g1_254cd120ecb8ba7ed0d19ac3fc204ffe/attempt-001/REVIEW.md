# Independent review

Advisory verdict: **REVISE**. The repaired pack is careful, reproducible in the available toolchain,
and unusually honest about its validation status. One deterministic conformance boundary remains
outside the normative contract. This review does not award `REVIEWED` or alter the candidate.

## Prioritized findings

### P1 — The reference imposes an undocumented 4,096-call-site limit

`REQUIREMENTS.md:30-47` presents the translation limits that define accepted capacity, including
65,536 source tokens and 65,536 bytecode instructions, but no call-site or relocation limit.
`sealed/reference/src/minic.c:25,129,468-470` instead fixes `MAX_PATCHES` at 4,096 and rejects the
next call even when every documented resource remains far below its limit.

An independent boundary probe used this valid shape:

```text
int f(){return 0;} int main(){ f(); ... 4,097 total calls ... }
```

The source has 16,418 bytes, 16,403 lexical tokens, 8,200 emitted instructions, two functions, and
zero arguments per call. The 4,096-call variant exited 0. The 4,097-call variant exited 65 with
`too many function calls`. That makes valid-input behavior depend on a hidden implementation table,
contrary to the pack's explicit, deterministic language contract and the reference README's claim
to implement the exact language.

Repair by either sizing/streaming call resolution so documented limits are the binding limits, or
adding a normative call-site capacity with rationale and exact/one-over tests. Keep the rejection
safe and deterministic in either design.

### P2 — Incremental learner feedback is thin (non-blocking)

The starter moves from safe loading to an entire lexer, compiler, resolver, and VM behind one TODO.
The six public language cases are useful end-to-end checks, but there are no milestone-level lexer,
parser, bytecode, or VM checkpoints. For a difficulty-8 challenge this is usable, but a small set of
non-solution intermediate contracts or tests would make failures much easier to localize.

## Evidence assessment

The supplied evidence was treated as claims and rerun rather than accepted as proof. In a writable
scratch copy, both strict C11 builds succeeded; the process-control tests passed 4/4, the public
reference suite 18/18, and the sealed suite 34/34. The nested Mini-C bytecode interpreter printed
exactly `42`. The intentionally incomplete starter reproduced 12 passes and 6 expected failures.
Two clean builds yielded identical executable digests.

A separate bounded matrix covered semantics and exact/one-over source, bytecode, function,
parameter, local, frame, operand-value, identifier, and nesting boundaries. It passed 22/23 at the
default optimization and identically at `-O0` and `-O3 -flto`; only the undocumented call-patch
boundary failed. This is strong targeted evidence, not exhaustive conformance or a completion label.

## Disclosure, provenance, and licensing

Solution-bearing answers and the full reference are consistently below `sealed/`; learner-facing C
is confined to `starter/`. An independent walk found no special files, common credential signatures,
answers outside `sealed/`, or misplaced C sources. The actual learner export/view was not available,
so exclusion of `sealed/` at transfer time remains unverified.

Manifest and provenance identifiers, source commit, and snapshot linkage agree. The license boundary
clearly separates the CC0 catalog snapshot, the `NOASSERTION` linked resource, and the limited
personal-education permission for generated files. The upstream resource was not available, so the
authorship/no-copy statement and upstream license status remain provenance assertions rather than
independently verified facts.

## Validation honesty and learner value

The artifact consistently remains `GENERATED` + `PARTIAL`, requires independent validation, and
disclaims `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, and
`PRODUCTIONIZED`. Reproduced builder observations matched their report. Limitations around fuzzing,
sanitizers, portability, sandboxing, benchmarking, and production use are stated plainly.

The normative grammar, error categories, semantic rules, design questions, debugging exercise, and
explicitly bounded bootstrap claim are useful and coherent. The public suite is correctly described
as incomplete, and the staged interpreter does not inflate its result into ISO C or full self-hosting.

## Disposition

Revise the call-site capacity contract/reference and add its boundary regression. A separate
orchestrator-captured acceptance validator must decide any eventual `REVIEWED` promotion.
