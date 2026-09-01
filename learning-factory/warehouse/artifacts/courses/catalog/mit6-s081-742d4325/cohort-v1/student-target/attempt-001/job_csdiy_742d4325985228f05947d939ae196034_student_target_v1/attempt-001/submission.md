# Submission — `unit_kickoff_vmwalk_v1`

## Status

`SELF-CHECKED` for this kickoff unit only; controlled worker-harness validation is pending. This submission does not claim completion of MIT 6.S081, xv6 work, or any larger course plan.

## Submitted work

- Portable C11 implementation split across `src/main.c`, `src/vmwalk.h`, and `src/vmwalk.c`.
- `Makefile` producing `build/vmwalk` with the required strict compiler flags.
- Eighteen deterministic black-box tests in `tests/test_vmwalk.py` covering successful translation, modeled faults, parsing, atomic output, resource bounds, exact formatting, and exit statuses.
- Bounded design and comprehension responses, learner notes, debugging history, and labeled self-check evidence.

The implementation validates the complete input before output, uses fixed representations matched to the declared maxima, checks hexadecimal accumulation before overflow or truncation, and keeps modeled faults distinct from invalid input and internal failures.

## Reproduction

Run from the submission root:

```text
make clean all
make check
```

Both commands returned 0 in the recorded learner run. Exact command output and tool versions are in `evidence/build.log` and `evidence/test.log`. These logs remain learner-produced evidence and are not labeled `HARNESS-VALIDATED`.

## Deliberate boundary

There is no real page-table encoding, privileged instruction, TLB, page allocation, concurrency, memory access, or kernel integration. The optional sanitizer runtime was unavailable in the sealed environment; this does not replace or alter the required clean-build and behavioral checks.
