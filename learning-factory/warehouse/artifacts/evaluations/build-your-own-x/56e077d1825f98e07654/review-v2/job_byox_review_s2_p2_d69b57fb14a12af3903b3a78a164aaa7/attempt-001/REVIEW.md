# Independent review

Date: 2026-09-02 (America/Chicago)

Advisory verdict: **REVISE**. The core reference is credible and independently
reproduced, but the evidence pack overstates its machine-readable adversarial
coverage and does not itself establish progressive-disclosure isolation. This
review does not assign `REVIEWED` or any other validation label.

## Prioritized findings

### P1 — Medium: machine-readable adversarial coverage is overstated

`CANDIDATE/adversarial/README.md` says `cases/boundaries.json` covers stale PID
reuse, duplicate or mismatched scheduler state, a translation ending at
`0xffffffff`, full-capacity RAMFS create, and scrub-before-reuse. The JSON has
six vectors and contains none of those cases (although it does contain terminal
PID, frame-range, combined-permission, addition-wrap, and null/zero cases).

This is a documentation/evidence defect, not a demonstrated reference-code
failure: the sealed suite covers several omitted cases, and the reviewer edge
harness passed the missing scheduler and VM behaviors. Still, an evaluator
following the advertised machine-readable plan would silently skip material
boundaries. Add the missing vectors and a deterministic executor, or narrow the
README claim to the six cases actually present.

### P1 — Medium validation gate: disclosure is described, not demonstrated

The candidate contains 41 files beneath directories named `sealed`, including a
reference implementation, reference tests, and exercise answers. Keeping these
in the evaluator bundle is reasonable, and no such directory appears beneath
the three core learner roots (`starter`, `public_tests`, and `environment`).
However, the only learner/evaluator allowlist is prose in `AGENTS.md`; the
manifest has no machine-readable exposure map, and the claimed structure check
does not construct or inspect an actual learner view.

Do not treat the current layout scan as proof of isolation. Before publication,
an orchestrator-controlled validator should materialize the exact student view
from an explicit allowlist, recursively reject every sealed/reference/answer
path and special link in that view, and retain the resulting inventory. If that
external evidence already exists, this item becomes a limitation rather than a
candidate-content change.

### P2 — Low: byte-snapshot evidence is not fully portable

`lf_ramfs_init` and `lf_vm_space_init` initialize members but not structure
padding. A reviewer probe prefilled storage and observed 24 residual bytes in
`lf_ramfs_t` and 32 in `lf_vm_space_t`; two logically initialized objects were
not byte-identical. The public and sealed tests then use structure assignment
followed by `memcmp` for mutation snapshots. C permits padding bytes to take
unspecified values during structure assignment, so those checks are not
portable proof of the stated byte-for-byte property even though they pass with
the configured GCC.

Use an explicit raw-byte snapshot (for example, `memcpy` into an unsigned-byte
buffer) or canonicalize the whole representation without hosted dependencies.
Also clarify whether padding belongs to the normative filesystem state.

### P3 — Low: one retained binary is path-dependent

The submitted and cleanly rebuilt target ELF/BIN artifacts are byte-identical.
By contrast, `sealed/reference_tests/build/test_reference` differs after a clean
rebuild because `-g` embeds the absolute builder workspace path. The submitted
binary exposes the builder job directory in its debug strings. Either omit this
scratch executable from the package or apply a debug-prefix map and record its
hash if byte reproducibility is intended.

### P3 — Low: generated-material reuse terms remain unspecified

The license boundary correctly limits CC0 to the catalog metadata and records
the linked project as `NOASSERTION`; it does not misapply that status to linked
code. But “independently generated for personal educational use” is not an
explicit license grant for the generated starter, tests, or prose. Record the
chosen license or an explicit all-rights-reserved distribution policy before
sharing the pack beyond the authorized learning environment.

## Confirmed strengths

- Clean reference and starter cross-builds reproduced every submitted target
  build product byte-for-byte.
- The reference passed the public suite, the 400-check sealed suite, and 28
  additional reviewer checks with ASan/UBSan active.
- QEMU exercised reset, UART, MMU enablement, VM/RAMFS behavior, context
  switching, and task return, producing the exact ordered markers and CRLF.
- The ELF target, segment permissions, non-executable stack, and lack of
  undefined symbols match the contract.
- The incomplete starter is honest and useful: it builds, fails 37 behavioral
  checks, contains staged safe-failure stubs, and is not a copied solution.
- Requirements, concepts, design questions, isolated exercises, and explicit
  non-goals provide strong learner guidance without claiming production fitness.
- Manifest labels and validation prose correctly refrain from self-promoting to
  `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
  `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.

## Decision

Resolve the adversarial-vector mismatch and obtain deterministic, orchestrator-
captured learner-view evidence before reconsidering PASS. The padding,
path-reproducibility, and generated-license points are lower-risk follow-ups.
Nothing observed warrants FAIL: independently exercised reference behavior met
the defined core contract.
