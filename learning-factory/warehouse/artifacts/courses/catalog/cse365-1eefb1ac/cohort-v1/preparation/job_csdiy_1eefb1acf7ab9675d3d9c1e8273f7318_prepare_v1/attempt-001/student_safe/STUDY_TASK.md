# Study task: build a safe local inspection adapter

## Scenario

A larger application needs file metadata from a trusted Python helper process. Callers are allowed to choose one of two operations and name a file inside a designated workspace, but every caller-supplied value is untrusted. Build the boundary between the application and the helper so that the request stays data rather than becoming executable syntax.

Use Python 3.11 and the standard library. The exercise must run offline.

## Functional contract

Implement a package named `process_boundary` with a public operation equivalent to:

```text
run_inspection(action, target, workspace, timeout_seconds) -> InspectionResult
```

Define and document the concrete `InspectionResult` representation. It must let a caller distinguish success, rejection before launch, child-process failure, and timeout without parsing a human sentence.

The trusted local helper must implement exactly these ordinary operations:

- `describe`: report a stable, machine-readable description containing the target's file size and whether it is a regular file;
- `digest`: report the target's SHA-256 digest.

Meet all of these requirements:

1. Accept only the two documented action names. A caller cannot select an executable, helper path, interpreter option, or extra argument.
2. Accept only a relative target that resolves to an existing regular file inside `workspace`. Reject absolute paths, traversal outside the workspace, and a symlink whose resolved destination is outside it.
3. Invoke the helper directly with an argument vector. Do not invoke a shell or assemble caller data into a command-language string.
4. Use a controlled working directory and a deliberately constructed minimal environment. Document every environment value inherited or supplied.
5. Launch the helper in a dedicated process group or session. Apply a positive bounded timeout; on timeout, terminate the whole group, use a bounded cleanup escalation if necessary, and reap the child.
6. Capture standard output and standard error separately, preserve the child exit status, and put an explicit size bound on captured diagnostic data.
7. Return deterministic structured failures. Do not silently retry and do not report a rejected or failed launch as success.
8. Keep the helper and all test fixtures inside the exercise project. The implementation must not use a network, privileges, or files outside the disposable workspace.

Choose a stable serialization for successful helper output and document it. Favor a small explicit interface over a general command runner.

## Required test matrix

Write automated tests that create their own temporary workspaces and cover at least:

- both allowed operations on an ordinary file;
- a filename containing spaces;
- the harmless literal filename `report;touch SHOULD_NOT_EXIST` and proof that no marker file is created;
- an unknown action and malformed values;
- `..` traversal and an absolute target;
- a symlink inside the workspace that resolves outside it;
- a missing target and a non-regular target;
- controlled child failure with separate captured diagnostics;
- a deterministic timeout using a test-only slow helper fixture;
- the documented output-size bound.

Tests must make their own assertions; a transcript showing commands were run is not a substitute for them. Keep timing margins large enough to avoid a race-prone timeout test.

## Deliverables

Use this layout or document an equally clear equivalent:

```text
safe_process_lab/
  README.md
  DECISIONS.md
  src/process_boundary/
  tests/
  evidence/test-output.txt
COMPREHENSION_RESPONSES.md
```

`README.md` must state how to run the tests offline, the public contract, supported platform, and known limitations. `DECISIONS.md` must identify assets, trust boundaries, plausible failure modes, enforced invariants, and at least two alternatives you considered. The evidence file must capture the interpreter version, exact test command, complete test summary, and exit status from a clean run.

Write responses to the separate comprehension prompts in `COMPREHENSION_RESPONSES.md`. Do not edit the prompt file.

## Suggested timebox

- 45 minutes: interface, threat model, and invariants
- 2 hours: helper and adapter implementation
- 90 minutes: adversarial and failure tests
- 45 minutes: documentation and decision record
- 30 minutes: clean run, evidence capture, and comprehension responses

Stop after eight hours. Preserve honest evidence of incomplete or failing work rather than weakening a requirement.
