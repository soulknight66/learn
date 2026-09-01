# Kickoff Revision Notes

Provenance: fresh learner-authored notes based only on the supplied learner material, prior attempt,
examiner feedback, and experiments in this workspace. Validation label: `LEARNER_SELF_CHECKED`, not
independently validated.

## Scope and change from the prior attempt

This revision remains limited to `unit_kickoff_trustworthy_convex_allocation_v1`. The examiner found
that the prior workspace contained prose claims but no runnable implementation, tests, design,
validation record, or comprehension responses. My initial file inventory confirmed that gap.

I added the missing `src/allocation_solver/` package, four test modules, `README.md`, `DESIGN.md`,
`VALIDATION.md`, all ten comprehension responses, and a `validation-evidence/` directory with raw
fixtures, exact process outputs, hashes, and independent learner arithmetic. I wrote these three
revision records fresh and left `LEARNER_MATERIAL/`, `PRIOR_ATTEMPT/`, and `EXAMINER_FEEDBACK/`
unchanged.

## Engineering conclusions

- Positive weights make the diagonal quadratic strictly convex. The budget simplex is nonempty,
  compact, and convex, so the optimizer exists and is unique.
- Sorting is an internal threshold calculation, not a coordinate permutation. Applying the
  threshold back to the original vector is essential to keep amounts attached to the correct IDs.
- Convergence needs both the projected fixed-point residual and the feasibility residual. The
  one-update exhaustion fixture demonstrates why a feasible point can still be nonstationary.
- Input validity, binary64 evaluability, and convergence are separate states. They now have distinct
  deterministic error/status documents, streams, and exits.
- Raw-byte hashing must occur before decoding: even a final newline changes provenance while leaving
  the parsed JSON meaning unchanged.
- A fixed activation charge is not a small smooth extension. Near a support boundary, its fixed
  jump dominates the quadratic's second-order Jensen gap, so the convex projected-gradient
  guarantees do not carry over.

For the supplied three-item sample, the run emitted
`(0.5142857120180376, 0.25714285900887307, 0.2285714289730893)` after 40 updates. The analytic
all-active solution is `(18/35, 9/35, 8/35)`, so the observed error scale is consistent with the
reported fixed-point tolerance. A separate script recomputed objective
`0.07142857142857145`, fixed-point residual `8.228356884742993e-10`, and zero feasibility residual
without importing production solver code; every recorded difference was zero.

## Concrete observations

The system `python3` is 3.6.8, while the unit requires 3.11. Using the provided CPython 3.11.5
binary, all six package modules compiled and the final discovery run executed 28 named tests with
additional subtests, exited 0, and ended `OK`.

Four bounded real-process checks reproduced their snapshots exactly:

- sample: exit 0, 642 stdout bytes, empty stderr, `CONVERGED`;
- one-update case: exit 3, 574 stdout bytes, empty stderr, `MAX_ITERATIONS` with fixed-point residual
  `0.12498750000000003`;
- finite overflow-prone case: exit 4, empty stdout, 116-byte `NUMERICAL_FAILURE` stderr;
- malformed JSON: exit 2, empty stdout, 101-byte `INVALID_INPUT` stderr.

## Remaining uncertainty

All evidence is learner-controlled. Binary64 projection can retain finite rounding error; absolute
tolerance is scale-sensitive; high weight ratios can converge slowly; and the grid oracle has only
`0.001` spacing in one two-item case. No harness-controlled validation or transfer check has
occurred. These notes make no claim about later units, EE364A completion, or whole-course completion.
