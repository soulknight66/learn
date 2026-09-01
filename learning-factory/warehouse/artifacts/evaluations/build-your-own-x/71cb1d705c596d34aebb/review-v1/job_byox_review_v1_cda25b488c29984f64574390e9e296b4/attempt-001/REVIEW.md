# Independent review

Verdict: **REVISE**. The pack is thoughtful, unusually candid, and mostly
reproducible on the available Linux toolchain, but two correctness conflicts
and an unproven disclosure boundary block acceptance. Nothing in this review
promotes the candidate beyond its existing `GENERATED` and `PARTIAL` labels.

## Prioritized findings

### P1 — The permanent public suite rejects a conforming completed solution

`public_tests/test_starter.py:81-89` invokes the nonempty command
`not-implemented` and requires status 2 plus the exact internal message
`tokenization is a TODO`. That is a scaffold-state assertion, not a stable
contract. `REQUIREMENTS.md:103-105` requires an unlocatable command to return
127. The sealed reference accordingly returned 127 and
`minish: not-implemented: No such file or directory` for the same `-c` bytes.

This contradicts `README.md:54-63`, which tells learners to replace TODOs
incrementally and makes passing the public suite part of completion. The test
will fail as soon as the lexer advances, and no completed implementation can
satisfy both it and the command-status contract.

Repair direction: separate one-time scaffold smoke tests from durable public
conformance tests, or tag tests by milestone. A physical-line test for a
completed shell should assert observable output/status, never a TODO message.
Add public, stage-appropriate checks for the suggested lexer, parser, process,
descriptor, job, and terminal milestones so progress yields useful feedback.

### P1 — Foreground continuation is mistaken for a stopped job

`sealed/reference/minish.c:1021-1025` waits for a foreground process group with
`WUNTRACED` only. Although the background reaper requests `WCONTINUED`, this
foreground path cannot update a process recorded as stopped when another
pipeline member resumes the group.

Independent reproducer:

```sh
sealed/reference/minish -c \
  "sh -c 'kill -STOP \$\$; sleep 0.30' | sh -c 'sleep 0.05; kill -CONT 0; sleep 0.10'"
```

Observed status was 147 (`128 + SIGSTOP`). The first stage had already resumed,
so the contract at `REQUIREMENTS.md:225-230` requires the job to remain
`Running` until all members finish; the final-stage status should then be 0.
In an interactive run, the same stale aggregate can also make the shell reclaim
the terminal while a resumed member is still running.

Repair direction: collect continued events in the foreground wait and do not
declare the aggregate stopped while an already-pending continuation remains
unconsumed. Add a bounded regression in which one member stops and another
member resumes the process group before exiting.

### P1 — Progressive disclosure is named, but not enforced by the artifact

The reviewer can read the complete solution at
`CANDIDATE/sealed/reference/minish.c`, reference tests and design answers under
`CANDIDATE/sealed/`, fixed debugging answers under `debugging/*/sealed/`, and
review answers under `review_exercises/*/sealed/`. `README.md:21-23` says this
material is outside the learner view, but `MANIFEST.yaml` contains no audience
mapping or export allowlist. `AGENTS.md` merely asks learner agents not to look.

A separate factory layer may know how to filter these paths, but that policy
and its output are not evidence in this submission. If `CANDIDATE/` itself is
delivered, the answer keys are directly exposed. A path name and prose request
are not an access boundary.

Repair direction: define the learner view with a deterministic, machine-readable
allowlist; generate it outside the sealed tree; and validate that no sealed
path, answer text, reference binary/source, or instructor-only test is present.
Retain the validator view separately and record both view digests.

### P2 — No-argument mode hangs when standard input starts closed

This bounded command timed out with status 124 and no diagnostic:

```sh
timeout 1s sealed/reference/minish <&-
```

At `sealed/reference/minish.c:1728-1735`, the signal self-pipe is created after
testing fd 0. With fd 0 initially closed, the pipe can reuse it. The input loop
then polls fd 0 both as standard input and as the self-pipe
(`minish.c:1897-1904`) and waits forever. The candidate's sealed review broadly
notes that closed standard descriptors lack coverage, but it does not identify
this concrete nontermination.

Repair direction: validate/reserve standard descriptors before opening internal
ones, keep internal descriptors above fd 2, handle `POLLERR`/`POLLNVAL`, and add
a bounded closed-stdin regression.

### P2 — Exact generated-artifact provenance is not integrity-bound

The metadata consistently binds the topic to source ID, commit, and catalog
snapshot, and its license boundary is commendably conservative. It does not,
however, record a generator/job identity, generation parameters, a per-file
inventory, or a digest of this candidate tree. The manifest's
`provenance_sha256` equals `PROVENANCE.json`'s internal `snapshot_sha256`, but
is not the file's SHA-256 (observed file hash:
`1af66d8f2f62445463a14c74c203620c23213bed4cb5e31eaada2408e3e4c1f1`).
Without a supplied schema, that may be an intended source-snapshot pointer, but
it cannot integrity-check the provenance document or reproduce this exact pack.

Repair direction: add an explicit artifact inventory/tree digest and generator
job/tool identity, define what each digest covers, and remove or clearly mark
the machine-local source path. Keep the current source-snapshot fields as a
separate upstream provenance layer.

### P3 — Generated material is intentionally unlicensed

`LICENSE_BOUNDARY.md:13-15` expressly says the generated-material statement is
not a license grant. This is honest and preferable to claiming rights in the
linked `NOASSERTION` tutorial, but it leaves learners and educators without
clear permission to redistribute or adapt the challenge, starter, tests, or
answers outside the factory's private-use context. If reuse is intended, add a
license for material the generator is authorized to license while preserving
the linked-resource boundary.

## Confirmed strengths

- The requirements precisely define grammar, statuses, redirection ordering,
  builtin context, process groups, terminal ownership, and shutdown behavior.
- `CONCEPTS.md` and `DESIGN_QUESTIONS.md` provide useful mental models without
  directly disclosing the implementation.
- With a workspace-local `TMPDIR`, the strict starter build/public suite passed
  9/9 and the reference suite passed 51/51, including four PTY cases. A clean
  repeat build produced the same binary SHA-256 in the same workspace.
- The ten adversarial inputs are honestly described as a corpus without an
  oracle. The benchmark harness likewise avoids thresholds and does not claim
  `BENCHMARKED`.
- The debugging and review exercises are focused and useful. Bounded runs
  reproduced the documented EOF hang, sequential-pipeline hang, wrong-child
  status, and corresponding fixed outcomes.
- Both metadata documents parse as strict JSON; project/source/commit/snapshot
  identities agree; the manifest remains `GENERATED`, `PARTIAL`, independently
  unvalidated, and not productionized.
- No symlink, special file, checked-in binary/object/archive/bytecode, or
  credible credential was found in the immutable candidate tree.

## Review limitations

The upstream repositories and authoritative student-view policy were not in
the workspace, network access was restricted, and `git` was unavailable. Thus
the source commit, upstream licenses, no-copy assertion, and actual learner
export could not be authenticated. ASan and UBSan runtimes, Valgrind, Clang,
and fuzzing tools were unavailable. Testing was Linux-only; no syscall fault
injection, sustained race campaign, low-resource matrix, or production review
was performed. Candidate-authored tests were rerun as reproducibility evidence,
not treated as independent proof of any stronger validation label.
