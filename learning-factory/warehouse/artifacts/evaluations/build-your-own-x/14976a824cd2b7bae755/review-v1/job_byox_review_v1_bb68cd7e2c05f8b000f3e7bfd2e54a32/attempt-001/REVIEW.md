# Independent review

Verdict: **REVISE**.

The submission has a strong teaching concept, candid scope boundaries, and useful deterministic
control-plane coverage. Independent execution reproduced the builder's principal pass/fail summaries.
It is not ready to pass review, however: targeted checks found safety and lifecycle defects outside
the supplied tests, and the submitted artifact does not itself establish a safe learner projection or
an explicit license for its generated content.

## Prioritized findings

### P0 — Prospective-path resolution fails open when Bash cannot allocate the here-string

`CANDIDATE/sealed/reference/lib/runtime.sh:79` populates the path-component array with a here-string
but does not check `read`'s status. If Bash cannot create the here-string temporary object, the array is
empty; the function reaches `runtime.sh:105`, prints its initial value `/`, and returns success. The
disjointness check then proceeds with the wrong resolved state path.

With `TMPDIR=/definitely/nonexistent`, an attempted create using `MINICTR_HOME=ROOTFS/state` emitted a
raw Bash temporary-file error, returned 0, and created `ROOTFS/state/containers/overlap/rootfs`. This
directly violates the before-write containment rules in `CANDIDATE/REQUIREMENTS.md:53-54,68-69` and
also bypasses the required `minictr:` diagnostic boundary. The resolver must treat parsing or temporary
storage failure as fatal; this case needs a deterministic regression test.

### P1 — Name validation is locale-dependent and can strand state

The bracket ranges at `CANDIDATE/starter/minictr:35` and
`CANDIDATE/sealed/reference/lib/runtime.sh:40` are evaluated under the caller's locale. With the
available `en_US.utf8` locale, the supposedly ASCII grammar accepts `é`. Independent create and `ps`
both succeeded. A later invocation under `LC_ALL=C` omitted the registration from `ps` and rejected
`delete é`, leaving state that the CLI could no longer manage.

This contradicts `CANDIDATE/REQUIREMENTS.md:45`. Make validation bytewise independent of ambient
locale and add cross-locale tests.

### P1 — A zombie owner is reported as a live run

`minictr_read_live_pid` at `CANDIDATE/sealed/reference/lib/runtime.sh:317-333` validates only PID and
start token. It does not use the process-state rejection already implemented at `runtime.sh:258-276`.
A disposable record containing a real zombie PID and its matching token was printed as `RUNNING`.

An unreaping parent can retain a zombie indefinitely, so subsequent run/delete operations can remain
blocked. This violates the stale-run requirement at `CANDIDATE/REQUIREMENTS.md:97-98`. Liveness must
also reject `Z` and `X`, with a regression covering `ps`, `run`, and `delete`.

### P1 — Progressive disclosure is not established by the submitted artifact

The artifact contains 25 readable files below `sealed/` paths, including the complete reference
runtime, evaluator tests, fixed debugging solutions, and model code reviews. The instructions at
`CANDIDATE/AGENTS.md:9` and `CANDIDATE/debugging/README.md:14-16` rely on learner restraint; the
manifest has no learner-view allowlist. In addition, top-level `CANDIDATE/VALIDATION.md:106-129,180-236`
names hidden cases, fixed answers, and exact signal expectations, so filtering only `sealed/`
directories would still disclose evaluator strategy.

If the factory has an external deterministic projection, that projection was not supplied and cannot
be transfer-verified here. Before release, define the learner allowlist, sanitize builder validation
for that view, recursively exclude every nested `sealed/` directory, and retain harness-controlled
evidence that the transferred view contains no answers or hidden graders.

### P2 — Wrapper-directed TERM does not retain TERM semantics at the payload

The runtime trap at `CANDIDATE/sealed/reference/lib/runtime.sh:531` signals only its direct isolator.
The default isolator execs `unshare --kill-child` at
`CANDIDATE/sealed/reference/lib/isolate.sh:103-113`; util-linux defaults that child-death signal to
`SIGKILL`. A bounded process-only reproduction printed `payload_ready` and returned 143 after TERM,
but the payload's TERM trap never ran. Thus a TERM received by the wrapper becomes KILL at the
namespaced child rather than satisfying the strong recommendation in
`CANDIDATE/REQUIREMENTS.md:114-115`.

Clarify and implement the desired signal/process-tree contract, then exercise the real isolator rather
than only the fake helper.

### P2 — The environment checker gives a false reproducibility assurance

`CANDIDATE/environment/README.md:12-13` lists usable temporary storage as a prerequisite, but
`CANDIDATE/environment/check.sh:43-55` checks only command presence and reports “public-test
prerequisites found” at line 82. This workspace has no `/tmp`; the checker returned 0 while the exact
documented public, reference, adversarial, and benchmark commands failed before their tests ran.

Check that `${TMPDIR:-/tmp}` exists, resolves safely, and supports private temporary creation, or make
the documented commands choose a workspace-local directory explicitly. This also needs to cover the
fail-open runtime condition above.

### P2 — Generated-content licensing and artifact integrity remain ambiguous

`CANDIDATE/LICENSE_BOUNDARY.md:3-11` correctly keeps the CC0 catalog facts separate from a linked
resource whose license is `NOASSERTION`. However, “independently generated for personal educational
use” is not an explicit license grant, and the 66 generated files have no `LICENSE`, `COPYING`,
`NOTICE`, or SPDX declaration. Learner modification and redistribution rights are therefore unclear.

The digest at `CANDIDATE/MANIFEST.yaml:5` correctly matches the canonical embedded `{project,source}`
object and `CANDIDATE/PROVENANCE.json:50`; it is not the byte hash of `PROVENANCE.json` and there is no
file inventory or tree digest. Accordingly, the statement at `CANDIDATE/LICENSE_BOUNDARY.md:13-14`
associates the pack with source metadata but does not cryptographically bind the submitted artifact
bytes. Add an explicit generated-material license and a deterministic artifact inventory/digest.
Remove or justify the internal host/user paths in `PROVENANCE.json:78` and `VALIDATION.md:248`.

### P3 — Several learner-facing checks are weaker than their stated lessons

- `CANDIDATE/public_tests/test_minictr.sh:426-460` starts two creates without a synchronization gate,
  so its atomicity result depends on scheduling rather than deterministically placing both callers in
  the vulnerable interval.
- The overlap assertions at `public_tests/test_minictr.sh:207-208,227-228` look only for the reference
  layout names `containers` and `locks`, even though `REQUIREMENTS.md:70` says layout is not public.
- The argv debugging test never uses a nonzero fixture despite the status objective in
  `debugging/01-argv-boundaries/README.md:15`; the atomic-create exercise does not prove that a losing
  writer cannot overwrite the winner despite `debugging/02-atomic-create/README.md:12-14`.
- `CANDIDATE/README.md:51` points to an unnamed “threat model,” and its repository guide omits the
  debugging, review, adversarial, and benchmark materials. Learner rootfs guidance also omits the
  reference's mandatory real `proc/` mountpoint.

These gaps do not erase the passing checks, but they reduce the strength and discoverability of the
feedback learners receive.

## What is working well

- With a valid `TMPDIR`, independent runs passed the sealed reference suite (19/19), public reference
  suite (9/9), adversarial suite (34/34), all three fixed debugging examples, and the real namespace
  smoke on this host.
- The untouched starter produced its intentional 3-pass/6-fail baseline, making incompleteness clear
  rather than manufacturing a green result.
- The staged progression from deterministic lifecycle work to host-dependent namespaces is
  pedagogically sound, and the concepts/design material explains the control-plane/data-plane split
  well.
- Public-test and production-security limitations are unusually candid. The manifest remains
  `GENERATED` + `PARTIAL`, requires independent validation, and sets `productionized: false`.
- The upstream license remains `NOASSERTION`; no promoted validation label, copied-upstream claim, or
  benchmark generalization is made.

## Disposition

Repair the P0/P1 correctness issues, define and transfer-test the learner projection, resolve the
generated-material license, and rerun both supplied and targeted checks. Keep the current manifest
labels unchanged; the observed passing scripts do not independently justify any promoted lifecycle
label.
