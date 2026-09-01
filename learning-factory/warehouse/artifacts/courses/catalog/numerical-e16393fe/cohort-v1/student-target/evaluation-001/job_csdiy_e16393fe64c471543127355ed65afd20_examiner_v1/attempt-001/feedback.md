# Independent evaluation

**Decision: FAIL — 12/100.**

The decisive problem is missing durable evidence. The workspace does not contain the claimed `ReliableBisection/` project, source, test entry point, design, README, metadata, or experiment. This activates the rubric's missing-artifact cap of 30, prevents source review and branch tracing, and makes the unit incomplete regardless of the quality of the prose.

## Independent checks

| Check | Observed result |
|---|---|
| Full workspace inventory | Only the examiner inputs and `.factory-workspace`; no submitted project files |
| Required project/source/test paths | Exit 2: `No such file or directory` |
| `julia --version` | Exit 127: `julia: command not found` |
| Documented offline test | Could not start from `ReliableBisection/` because the directory is absent; the wrapper also exited 127 after failing to find Julia |

The reported file/token check and all cited source lines and testsets are self-reported claims here: none can be reproduced from the transferred artifacts.

## Score breakdown

| Criterion | Score | Reason |
|---|---:|---|
| Contract and result design | 0/15 | `DESIGN.md`, README, API, and result type are absent. |
| Numerical reasoning and invariant preservation | 0/25 | No implementation exists to inspect or manually trace. |
| Bounded, robust implementation | 0/15 | Core source is absent. |
| Deterministic test evidence | 0/25 | Test entry point is absent and no test ran. |
| Reproducibility and bounded evidence | 2/10 | The exact command and limitations are stated, but the project, Julia version, usage, and measured experiment are missing. |
| Comprehension | 10/10 | The written answers are technically sound and appropriately bounded, though their artifact citations are unverifiable. |

The numerical discussion shows good engineering judgment: it separates residual from interval width, identifies overflow and stagnation hazards, specifies cached evaluations, and avoids claiming runtime success. The main misconception is evidentiary rather than numerical: an inventory or token check performed on files that are not handed off is not durable proof that an examiner can score.

## Actionable next steps

1. Resubmit the complete `ReliableBisection/` directory with all six claimed paths, then verify the transfer from a fresh workspace.
2. In an environment with the declared supported Julia version, record `julia --version` and run `julia --project=. -e 'using Pkg; Pkg.test()'` from the project directory; retain output and exit status.
3. Fix any parse, dispatch, or behavioral failures found by that run rather than relying on static token presence.
4. Execute the three-scale experiment, replace every planned or `not run` value with measured data, and record command, version, inputs, outcomes, iterations, evaluations, and limitations.
5. Request re-evaluation only after a clean handoff can reproduce both the package tests and experiment offline.
