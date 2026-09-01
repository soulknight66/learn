# Independent review

Verdict: **REVISE**.

The challenge is substantially useful and its core reference behavior is well
corroborated, but one explicit CLI requirement is violated and the submitted
material does not itself demonstrate a safe learner/sealed projection. The
starter's incompleteness is intentional and honestly labeled; it is not the
reason for this verdict.

## Prioritized findings

### P1 — Usage failures violate the normative CLI contract

`CANDIDATE/REQUIREMENTS.md:91` requires usage failures to write one stderr line
beginning `mica: <phase> error:`. Both implementations instead print three
lines beginning `usage:` (`starter/src/mica.c:372` and
`sealed/reference/src/mica.c:1296`). An independent invocation with no arguments
returned 2 and produced exactly three stderr lines. Neither public nor sealed
tests cover this requirement, so a learner can copy the reference behavior and
still violate the published contract.

Make the contract and both implementations agree, then add a public assertion
for exit status, empty stdout, the prefix, and exactly one stderr line. If the
three-line help form is intended, revise the normative contract explicitly
rather than leaving the oracle inconsistent with it.

### P1 — Sealed isolation is asserted, not demonstrated

The root README says the reference, stronger tests, design answers, and review
findings are not learner-facing (`README.md:46`), and `AGENTS.md:24` tells the
learner not to inspect them. In the submitted tree, however, the sealed source,
tests, and answers have the same readable mode (0444) as learner files, and a
direct read succeeds. `verify_artifact.py` checks only that forbidden names do
not occur beneath three learner directories; it does not materialize or inspect
the actual student view.

If the control plane projects an allowlisted view, attach harness-controlled
evidence of that projection and test the resulting tree. Otherwise, package or
permission the sealed subtree so prose is not the access boundary. Until that
external step is shown, transfer isolation remains inconclusive rather than
verified.

### P2 — Completeness and content integrity are not reproducibly bound

The structural verifier's 23 required paths omit the starter C source and
Makefile, public test runner, reference source and Makefile, and sealed test
runner. In a disposable negative control, removing four core source/test files
still yielded status 0 and `required-paths: 23/23`.

The manifest field named `provenance_sha256` is also not a digest of the
submitted `PROVENANCE.json`: the values were respectively
`16c1f2...629b`, `6992ab...72d` for file bytes, and `89e2d6...8808` for
canonical JSON. It instead repeats the provenance object's internal snapshot
identifier. That may be schema-intended, but the current name and prose do not
give a verifier a cryptographic binding to the provenance file or other
artifact content.

Require every operational file and add a deterministic path/type/content-hash
inventory. Clarify the snapshot identifier's meaning and separately bind the
actual provenance object.

### P2 — The lexical whitespace contract is underspecified

The normative text says only that “Whitespace separates tokens”
(`REQUIREMENTS.md:8`). The supplied lexer accepts space, tab, carriage return,
and line feed, but rejects ASCII vertical tab (`0x0b`) and form feed. It also
implicitly defines LF-only line advancement and one-column tabs. A learner
using a reasonable ASCII-whitespace interpretation can therefore diverge from
the oracle.

List the accepted bytes and position rules explicitly, then add boundary tests.
The review observed `print<0x0b>1;` fail at 1:6 with a lexical error; this is a
contract ambiguity, not a claim that vertical tab must be accepted.

### P2 — Generated-material reuse terms are unclear

`LICENSE_BOUNDARY.md` correctly separates CC0 catalog metadata from a linked
resource whose license is `NOASSERTION`, and it states that linked content was
not copied. However, the artifact has no `LICENSE`, `COPYING`, or `NOTICE`, and
“generated independently for personal educational use” is not a clear license
grant for the generated documentation, C code, fixtures, and tests.

State explicit terms for generated material (or explicitly state that no
license is granted). The upstream CC0 and non-copy assertions could not be
independently checked offline and should continue to be treated as provenance
claims, not proof.

## What held up well

- The documented builds, partial starter baseline, two reference suites, and
  native Fibonacci smoke check reproduced from a clean disposable copy.
- Reviewer-authored boundary and semantic checks passed, including exact source,
  variable, AST-node, and depth limits; source-order declaration behavior; 160
  seeded expressions against an independent signed-64-bit oracle; and linked
  native equivalence.
- The C implementation avoids signed-overflow undefined behavior, bounds key
  resources, and handles division by zero and `INT64_MIN / -1` deliberately.
  Python subprocesses use argv arrays, timeouts, and captured output; no shell
  execution API or credential-shaped content was found.
- The learner path is coherent: contract, concepts, design questions, staged
  starter TODOs, public tests, adversarial cases, and follow-on exercises reveal
  material progressively at the document level.
- Validation claims are candid. The manifest remains `GENERATED` + `PARTIAL`,
  independent validation is required, sanitizer unavailability is disclosed,
  and no fuzzing, benchmark, review, transfer, or production label is claimed.

## Review limits

The available host was x86-64 with GCC 8.5.0. ASan/UBSan could not link, and
clang, valgrind, cppcheck, and scan-build were unavailable. The upstream source
and network were unavailable. No conclusion is made about other toolchains,
actual student-view transfer, licensing facts outside the submitted metadata,
fuzzing, benchmarks, or production readiness.
