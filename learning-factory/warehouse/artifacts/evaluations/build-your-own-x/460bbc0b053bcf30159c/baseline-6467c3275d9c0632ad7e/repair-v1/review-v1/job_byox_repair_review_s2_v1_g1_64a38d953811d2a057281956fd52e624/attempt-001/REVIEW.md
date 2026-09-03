# Independent review

## Advisory verdict

**PASS.** The reported process-entry validation defect is repaired, the repair is covered by an
independently authored regression, and no release-blocking correctness or evidence-integrity issue was
found. This verdict is advisory only; it does not publish a `REVIEWED` label.

## Prioritized findings

1. **No P0/P1 defect found — repaired boundary is correct.** `REQUIREMENTS.md:23` requires spawn
   entries below `CAIRN_USER_TOP`, and `REQUIREMENTS.md:92-93` applies that limit to every non-empty
   process. The reference rejects the boundary in `cairn_spawn` at
   `sealed/reference/src/cairn.c:156-158` and in `cairn_validate` at lines 637-639. A reviewer-written
   test independently confirmed rejection for ready, running, blocked, and exited states, while the
   maximum valid entry remained accepted.
2. **Low — preserve factory-side progressive-disclosure enforcement.** Learner material and solutions
   are cleanly partitioned (`starter/`, `public_tests/`, staged prompts, and `sealed/`), and no solution
   file appears below a learner work directory. The complete review pack necessarily contains the
   sealed subtree, however, so filesystem layout alone is not access control. The factory must exclude
   `sealed/` from the student view until the designated reveal stage.
3. **Informational — external provenance remains an evidence boundary.** `MANIFEST.yaml`,
   `PROVENANCE.json`, and `LICENSE_BOUNDARY.md` consistently identify the project, source, commit,
   CC0 catalog metadata, and the linked resource's `NOASSERTION` status. The upstream snapshot was not
   available in this workspace, so the claim that linked content was neither fetched nor paraphrased
   could not be independently authenticated.

## Correctness and reproducibility

Fresh strict builds of the starter and reference succeeded for hosted and freestanding targets. The
reference focused suite passed 10 cases, the public suite passed 4 cases, and the deterministic mixed
driver preserved invariants for 25,000 operations. Those builder-supplied drivers were treated as
corroboration, not self-proving evidence: the reviewer also compiled and ran a separate boundary test
with strict flags and with AddressSanitizer/UndefinedBehaviorSanitizer. GCC `-fanalyzer` reported no
diagnostics.

All 14 shipped non-sanitized executables/objects compared against fresh builds were byte-identical by
SHA-256. The freestanding core had no undefined symbols. The rebuilt kernel was ELF32 for Intel 80386,
booted under the pinned QEMU, printed `CAIRNOS: PASS`, and returned the documented debug-exit status
33.

## Learner usefulness and disclosure

The progression is useful and honest: concepts and a precise behavioral contract precede a compilable
TODO skeleton; public tests demonstrate style without claiming completeness; later prompts emphasize
boundary cases, invariant corruption, debugging, review, and performance methodology. The starter's
public-test failure is explicit and actionable rather than disguised as completion. Host modeling,
freestanding linking, emulation, and production OS behavior are clearly distinguished.

## Validation and license honesty

The candidate does not promote itself beyond `GENERATED` + `PARTIAL`. It explicitly calls the
25,000-operation driver deterministic rather than fuzzing, the one-shot timing result a probe rather
than a benchmark, QEMU a bounded smoke check, and the artifact non-productionized. The license boundary
does not borrow authority from the linked repository: catalog metadata is identified as CC0, linked
content remains `NOASSERTION`, and the generated content is described separately.

The remaining limitations are appropriate for an educational model: no real hardware matrix,
privilege boundary, external source authentication, transfer verification, security audit, or
production deployment was established or claimed.
