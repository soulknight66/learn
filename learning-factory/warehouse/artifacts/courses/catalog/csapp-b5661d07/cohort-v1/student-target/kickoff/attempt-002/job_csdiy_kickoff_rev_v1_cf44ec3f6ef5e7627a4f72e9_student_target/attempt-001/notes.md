# Revision Notes: Kickoff Unit 1

## Scope

This revision concerns only the manager-authored “Trustworthy Byte Histogram”
kickoff unit. It does not establish completion of CSAPP or of any wider course,
and it does not claim transfer verification. I used only the supplied learner
material, the prior attempt, the examiner feedback, and local build tools.

## What changed

The examiner could not assess the prior handoff because it contained narrative
files but no `submission/` directory. This revision adds the complete required
tree: build recipe, public interface, two C implementation files, C module
checks, Python black-box tests, README, design, test report, and all nine
comprehension responses. The root summary and debugging log were rewritten to
describe this revision rather than merely referring to the absent artifact.

The implementation keeps the histogram opaque, reads through a fixed-size
unsigned-byte buffer, rejects count overflow before mutation, delays reporting
until successful input completion and owned-file close, checks report writes
and the final flush, and maps a closed pipe to an ordinary output failure where
`SIGPIPE` is available.

## Concrete experiments and observations

| Experiment | Observation |
| --- | --- |
| `make clean all` | Strict C11 compilation and linking completed with status 0. |
| `make test` | The module checks passed and all 9 Python CLI methods passed. |
| Boundary inputs | Exact reports passed at 4095, 4096, 4097, 8191, 8192, and 8193 bytes. |
| Negative I/O cases | Missing input and a directory input left stdout empty with status 1; a closed output pipe also returned status 1. |
| Overflow module checks | Attempts to increment a histogram already at `UINT64_MAX` were rejected without changing total or counters. |
| UBSan retry | Compilation succeeded, but linking failed because `/usr/lib64/libubsan.so.1.0.0` was unavailable; no sanitizer pass is claimed. |
| Final cleanup | `make clean` removed `build/` and `tests/__pycache__`, leaving source and documentation only. |

## Remaining evidence boundary

Allocation failure, owned-input close failure, and an unusual short positive
read with neither stream flag were not forced by the local suite. The source
contains explicit policies for them, but only the worker-controlled validator
can determine whether this bounded unit should be promoted.

---

Provenance: learner-authored from the supplied files and concrete local command
results observed on 2026-08-31.

Validation label: `LEARNER_REVISION_NOTES_NOT_COMPLETION_EVIDENCE`.
