# Learner agent guide

This repository is a progressively revealable systems exercise. Work only on learner-visible files,
normally under `starter/`, and treat the public contract as authoritative.

## Scope

- Implement the CLI described in `REQUIREMENTS.md`.
- Do not inspect, summarize, copy, or modify `sealed/`; it is evaluator-owned material.
- Do not modify `MANIFEST.yaml`, `PROVENANCE.json`, `VALIDATION.md`, or provenance/license records.
- Do not weaken or rewrite public tests to make an implementation pass.
- Do not fetch or copy an upstream implementation. The exercise must remain independently implemented.

## Routine commands

Run from the repository root:

```bash
./environment/check.sh
bash -n starter/minictr starter/lib/runtime.sh starter/lib/isolate.sh
bash public_tests/test_minictr.sh
```

The initial starter is incomplete, so functional tests are expected to fail until TODOs are implemented.
The public suite itself must remain privilege-free and deterministic.

## Shell engineering constraints

- Treat CLI arguments, environment values, rootfs paths, and metadata as data.
- Never use `eval`, source state files, or route controlled text through `bash -c`/`sh -c`.
- Preserve argv with Bash arrays and quoted expansions.
- Validate a name before using it in a path.
- Keep every state and cleanup target below an absolute `MINICTR_HOME`.
- Reject any canonical overlap between `MINICTR_HOME` and a registered rootfs before creating state.
- Never delete, mutate, or recursively traverse the registered rootfs during lifecycle cleanup.
- Use atomic filesystem operations for claims and bounded waits for locks or processes.
- Keep diagnostics on stderr and command output/status transparent after launch.

## Safety boundary

Public tests replace the isolator through `MINICTR_ISOLATOR`; they must not call `unshare`, `mount`,
`chroot`, `sudo`, or the network. Run real-isolation experiments only as an explicit separate step in a
disposable Linux environment with a caller-supplied rootfs.

The default isolator must fail closed. If a namespace, UID mapping, private mount, proc mount, or root
change cannot be established, it must not execute the user command on the host as a fallback.

## Evidence

Report control-plane tests and real-isolation checks separately. A green fake-isolator suite proves
argv and lifecycle behavior, not kernel isolation. Record exact commands and honest blockers; do not
claim production security from this exercise.
