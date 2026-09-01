# Minibox starter workspace

This is the only directory learners should modify. Implement the `minibox`
package here while preserving the module names and signatures in
`../REQUIREMENTS.md`.

Run the suite from the repository root so imports resolve consistently:

```bash
python3 -c 'import sys; print(sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
```

## Suggested progression

Work through one boundary at a time:

1. `minibox.config` and the domain exceptions
2. `minibox.rootfs`
3. `minibox.plan`
4. `minibox.state`
5. `minibox.runtime` with a fake backend
6. `LinuxSubprocessBackend` and child setup, only as an optional integration
   exercise

Keep each deterministic stage independent of the optional Linux stage. Importing
the package and running core tests must not call `unshare`, enter a namespace,
or inspect Linux-only paths.

## Required surface

The implementation is organized around these names:

```text
minibox.errors
  MiniboxError, SpecError, RootfsError, StateError, StateCommitUncertain
  BackendError, BackendUnavailable, BackendTimeout

minibox.config
  ContainerSpec, from_dict, load_spec

minibox.rootfs
  resolve_executable

minibox.plan
  IsolationPlan, build_plan

minibox.state
  ContainerState, StateStore (including recover)

minibox.runtime
  ExecutionResult, Runtime, LinuxSubprocessBackend
```

`ContainerState` is the immutable state value returned by `StateStore`; its
observable attributes are specified in the requirements. `minibox._child` is
an internal entry point reserved for the optional namespace backend, not an
additional public API.

## Working discipline

- Use temporary directories for rootfs and state fixtures.
- Keep host-environment values out of a validated spec unless the spec itself
  contains them.
- Treat path components and persisted JSON as hostile input.
- Keep plan construction free of process execution and host capability probes.
- Make clocks and backends injectable rather than adding test-only global
  switches.
- Use subprocess argument lists only; never use `shell=True`.
- Leave terminal lifecycle records in place as evidence.

Do not read or modify `../sealed/`, and do not change public tests to accommodate
an implementation. A public test failure should be resolved by comparing the
behavior with the learner requirements.

Minibox is an educational runtime, not a safe executor for untrusted programs.
Real namespace experiments should use a disposable, non-root Linux environment
and benign payloads only.
