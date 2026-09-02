# Independent review

Verdict: **REVISE**.

The core learning pack is coherent and unusually well bounded, but the sealed reference violates two explicit CLI requirements. These are localized defects rather than a reason to discard the pack. `CANDIDATE/` was treated as immutable; all builds and executions used a disposable copy.

## Prioritized findings

### P1 — Token-mode errors leak partial stdout

`REQUIREMENTS.md` line 45 says diagnostics leave stdout empty unless earlier `print` statements executed before a runtime failure. `sealed/reference/src/main.c` lines 69-84 instead print each token as it is lexed.

Independent probe:

```text
input:  let x = 1;\nprint @;\n
mode:   --tokens
exit:   65
stderr: late-lex-error.sprig:2:7: error: unexpected byte '@'
stdout: six token records through the PRINT token
```

This is an ordinary malformed-input path and makes the reference disagree with the learner contract. Validate the entire token stream before publishing it, buffer token output, or explicitly change the contract. Add a regression with an error after at least one valid token.

### P2 — stdout I/O failures are ignored or assigned the wrong exit code

`REQUIREMENTS.md` line 44 assigns file-I/O failures exit 74. With stdout directed to `/dev/full`, the independent observations were:

| Mode | Exit | Diagnostic |
| --- | ---: | --- |
| normal | 70 | `failed to flush program output` |
| `--tokens` | 0 | none |
| `--disassemble` | 0 | none |

The VM detects its final flush failure, but `main.c` lines 134-136 maps every VM failure to runtime exit 70. Token and disassembly writes are unchecked. `sealed/REVIEW.md` line 18 acknowledges the latter two modes but omits the normal-mode misclassification. Propagate output-write status in all modes and distinguish I/O from language runtime failures; cover immediate and final-flush failures.

## Evidence that held up

- The starter, reference, and direct VM target compile cleanly under `-std=c11 -Wall -Wextra -Wpedantic -Werror -O2`.
- The supplied 10 public, 19 sealed black-box, and 10 direct VM cases all pass against the reference. The starter's documented initial result also reproduces: only empty-program and token-mode tests pass.
- Reviewer-authored checks passed 676 modeled arithmetic cases, 13 exact contract/capacity boundaries, and 11 direct malformed/valid VM cases. Repeating the black-box suite with `-ftrapv` also passed.
- The deterministic adversarial generator produced the same 10 files twice. The benchmark helper ran successfully, but its samples are only a harness smoke check.
- Progressive disclosure is well structured: learner inputs contain intentional compiler/VM stubs and representative tests, while reference code, answers, alternatives, review, and production notes are under clearly marked sealed paths. No special files or solution-signature leakage were found in the declared learner set.
- The requirements, concept map, milestones, debugger modes, design questions, debugging exercise, and review exercise form a useful learning progression.
- License/provenance language clearly separates the CC0 catalog metadata from the linked resource's `NOASSERTION` status and does not pretend to grant rights in the linked project. Machine-readable identities and hashes are internally consistent.
- Claims are conservative: the manifest remains `GENERATED` + `PARTIAL`, requires independent validation, and explicitly sets `productionized` false. No fuzzing, benchmark, transfer, review-publication, or production label is claimed.

## Review boundary

The upstream repository and immutable source snapshot were unavailable, so originality and upstream-license assertions could not be independently established. The actual student-view filter was also unavailable; sealed isolation was assessed from layout and declared boundaries. UBSan was unavailable, and the exact archive allow/deny audit in the builder record lacks enough submitted detail for exact replay.

This verdict is advisory. It does not publish a `REVIEWED` label; only the orchestrator-controlled acceptance validator may do so.
