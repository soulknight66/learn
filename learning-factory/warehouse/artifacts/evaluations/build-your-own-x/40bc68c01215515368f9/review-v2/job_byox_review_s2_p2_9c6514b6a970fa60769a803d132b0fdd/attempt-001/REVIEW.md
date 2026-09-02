# Independent review

## Verdict

**REVISE.** The submission is well organized and unusually candid about its validation level, but
the sealed reference violates three explicit behavioral requirements. Passing builder-authored suites
do not outweigh the independent counterexamples below and do not establish a REVIEWED label.

## Prioritized findings

### 1. High — the VM raw guard rejects valid source before the semantic budget

REQUIREMENTS.md:65-69 defines a shared 100,000-statement budget and permits a larger raw-instruction
guard for malformed bytecode that loops without TICK. REQUIREMENTS.md:82-85 also requires identical
engine outcomes for accepted source and matching kind/location for rejected source.

VirtualMachine.java:31-35 instead applies one lifetime counter to every instruction, including
compiler-produced bytecode. An independent probe used a loop with 6,000 iterations, one 100-term
addition statement, and one increment statement per iteration. This is only 18,003 semantic statement
dispatches:

~~~text
TREE: OK [6000]
VM:   LIMIT 3:247 raw instruction limit of 1000000 exceeded
~~~

For the analogous infinite loop, TREE reported the semantic limit at 2:14 while VM reported the raw
limit at 3:267. This also disproves the statement in sealed/DESIGN.md:15-18 that compiler-produced
programs use the shared semantic budget.

The raw guard must not preempt valid compiler output. Add regressions containing many instructions per
TICK for both a finite program and an infinite program, and ensure successful-output and LIMIT-location
parity.

### 2. High — a nonzero out-of-range decimal is silently changed to zero

REQUIREMENTS.md:22-23 requires out-of-range numeric literals to be located LEX errors. Lexer.java:
121-129 rejects non-finite overflow but accepts underflow returned by Double.parseDouble.

The reviewer formed the literal as:

~~~java
"0." + "0".repeat(400) + "1"
~~~

The lexer accepted it with literal value 0.0. That changes a nonzero source value into zero instead of
reporting LEX at 1:1. Add explicit underflow/range detection and boundary tests around the least
representable positive double.

### 3. Medium — malformed unreachable bytecode is accepted

REQUIREMENTS.md:84-85 says malformed bytecode must be rejected as a language error. The VM validates
only the instruction it dispatches (VirtualMachine.java:24-30) and returns as soon as it sees HALT
(lines 70-75). A BytecodeProgram whose code was [HALT, null] therefore returned [] successfully.

Either validate the complete bytecode structure before execution or narrow and document the bytecode
contract. As written, a null instruction is malformed regardless of reachability, so success is not a
conforming result. Add unreachable invalid-opcode, operand, constant-index, jump-target, and null-entry
cases.

### 4. Medium acceptance gate — sealed-material exclusion is not demonstrated

README.md:7-10 says sealed/ is absent from the learner view, but the reviewed artifact physically
contains the complete reference and reference tests. environment/audit.py checks that selected
solution-like paths are absent from starter/ and public_tests/; it does not construct or validate an
exported learner view.

The manifest correctly does not claim TRANSFER_VERIFIED, so this is not a labeling misrepresentation.
Before publication, an orchestrator-controlled validator must materialize the actual learner view and
prove that sealed/, hidden tests, review answers, and other non-learner files are inaccessible.

## Evidence that held up

- The exact Python 3.11.5 and Temurin JDK/javac 21.0.5 toolchains were available.
- The starter compiled cleanly with -Xlint:all -Werror.
- The public suite passed 9/9 against the reference and the sealed suite passed 16/16.
- The package audit reproduced all reported counts and found no symlinks, special files, or scanned
  credential signatures.
- Only Java standard-library imports are used.
- The learner contract, concepts, milestones, design questions, exercises, and separation of public
  from sealed tests are useful for an advanced learner.
- MANIFEST.yaml remains GENERATED + PARTIAL. VALIDATION.md accurately says the differential corpus is
  deterministic enumeration, not fuzzing, and claims no benchmark, productionization, transfer
  verification, or stronger validation label.
- sealed/REVIEW.md and the productionization plan candidly identify recursion, allocation, cancellation,
  isolation, fuzzing, and benchmarking limitations.

The reference's claim of being complete against the educational requirements is nevertheless
incorrect because the independent examples above fall directly within those requirements.

## Provenance and license boundary

MANIFEST.yaml and PROVENANCE.json are valid structured data and agree on project/source identity,
source commit, and snapshot identifier. The boundary consistently marks the linked resource
NOASSERTION and says linked content was not copied. The generated code has no third-party dependencies.

These are internally consistent declarations, not independent provenance proof. The immutable catalog
snapshot, cited CC0 evidence, and linked resource were unavailable in this workspace, so their hashes,
license, and the no-copy assertion could not be verified. The phrase "independently generated for
personal educational use" is also not a standard reuse license; any distribution beyond the stated
context needs an explicit licensing decision.

## Advisory status

This review does not edit or promote MANIFEST.yaml. Even after revision, only a separately captured
acceptance validator may publish REVIEWED.
