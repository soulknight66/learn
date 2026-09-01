# Independent assessment rubric: safe process boundaries

## Scope and outcome

Assess only `kickoff_unit_01_safe_process_boundaries`. A passing result means that this manager-authored kickoff unit is eligible for harness-controlled validation. It is not evidence that an official CSE365 challenge, module, or course has been completed.

Use the submitted implementation and independently observed behavior as primary evidence. Learner prose may explain a decision but cannot establish that the code has the claimed property. Run all work in an isolated disposable directory with no network access, credentials, privileged operations, or third-party targets.

## Required evidence check

Before scoring, locate:

- implementation of the adapter and trusted helper;
- automated tests and their fixtures;
- `README.md` and `DECISIONS.md`;
- a captured clean-run transcript with interpreter version, command, summary, and exit status;
- responses to all eight comprehension prompts.

If an item is missing, score its associated criterion as zero. Independently rerun the documented test command, then add focused temporary tests as needed. Do not accept the submitted transcript as a substitute for a rerun.

## Critical conditions

The unit cannot pass if reachable code does any of the following:

- sends caller-controlled text through a shell, `os.system`, or an equivalent command-language evaluator;
- lets the caller choose the executable, helper location, interpreter flags, or arbitrary additional arguments;
- accepts a target that resolves outside the designated workspace, including through a symlink;
- performs network, privileged, or third-party activity for the exercise;
- omits an enforced finite timeout, dedicated process group with bounded termination and reaping, or an enforced captured-output bound;
- fabricates, edits, or mislabels test evidence as a clean successful run.

A critical condition yields `NEEDS_REVISION` regardless of points. Preserve the observed failure and reproduction details.

## Scoring (100 points)

### 1. Scope, contract, and threat model — 12 points

- 4: The public input and structured result contract is unambiguous.
- 4: Assets, untrusted inputs, trust boundaries, and plausible failure modes are concrete.
- 4: The work remains a narrow inspection adapter and documents at least two considered alternatives.

### 2. Process-boundary implementation — 28 points

- 8: Direct argument-vector execution is used; caller data occupies only intended data arguments.
- 6: Executable, helper, interpreter options, operations, and argument count are controlled by code.
- 5: A positive finite timeout is enforced; a dedicated process group is terminated with bounded escalation and reaped; timeout has its own structured result.
- 4: Standard output, standard error, and exit status are captured distinctly with an enforced size bound.
- 3: Working directory and minimal environment are intentionally constructed and documented.
- 2: Rejection, launch failure, child failure, timeout, and success cannot be confused.

### 3. Input and path invariants — 20 points

- 4: Only the two exact operation names and well-typed bounded inputs are accepted.
- 6: Absolute paths and traversal are rejected using resolved path semantics rather than textual prefix matching.
- 5: Symlink escape is rejected and the policy is tested.
- 3: Missing and non-regular targets are rejected before ordinary helper use.
- 2: Validation failures are deterministic and reveal no unnecessary host detail.

### 4. Independent behavior and tests — 22 points

- 4: Both operations produce correct, stable output for an ordinary fixture.
- 4: Spaces and the semicolon-containing literal filename remain data; no marker side effect occurs.
- 6: Independent tests confirm rejection of unknown action, malformed values, absolute target, traversal, and external symlink.
- 4: Controlled child failure preserves distinct exit status and diagnostic channels.
- 4: Timeout and output-bound tests are deterministic, enforced, and leave no lingering test process.

### 5. Software-engineering quality and evidence — 10 points

- 3: Code has cohesive responsibilities, useful names, and no accidental general command-runner surface.
- 3: Tests isolate their state, assert behavior rather than logs alone, and do not depend on ordering or the network.
- 2: Offline reproduction instructions work in a clean environment.
- 2: Evidence is complete and agrees with the examiner's run; limitations are reported honestly.

### 6. Comprehension — 8 points

Award one point for each response that contains the corresponding essential reasoning:

1. Distinguishes data arguments from executable selection, options, and command grammar, then ties the distinction to the implemented interface.
2. Identifies shell parsing and uncontrolled interpolation as separate from digest-algorithm correctness.
3. States resolved containment, explains why string prefixes fail, and addresses traversal and symlink destinations.
4. Limits a timeout claim to bounded waiting and notes that resource limits, descendant cleanup, output, and side effects require separate controls.
5. Maps each outcome to machine-checkable fields rather than prose matching.
6. Defines a genuine general property, a safe input generator, and a falsifiable assertion.
7. Adds HTTP parsing, authentication or authorization, request sizing, concurrency, and remote error exposure while retaining the narrow domain operation.
8. Separates self-report, learner-controlled test evidence, and independent validator evidence and assigns each the correct evidentiary strength.

## Decision

- `PASS_UNIT`: at least 80 points, no critical condition, all required evidence present, and the examiner's clean run succeeds.
- `NEEDS_REVISION`: any critical condition, fewer than 80 points, missing required evidence, or a failed independent run.

Record the point total, decision, exact test invocation as an argument vector, exit status, relevant output or artifact locations, and any independently reproduced failure. Only the worker harness may promote the persisted unit state after this assessment.
