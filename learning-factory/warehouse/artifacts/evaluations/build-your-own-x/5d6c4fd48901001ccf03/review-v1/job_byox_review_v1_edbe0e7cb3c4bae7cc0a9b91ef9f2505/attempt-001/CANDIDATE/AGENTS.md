# Learner and coding-agent guide

Implement Minibox only inside `starter/`. Treat every configuration document,
root filesystem, state file, executable name, and subprocess result as
untrusted input.

## Allowed work

- Read the learner-facing Markdown files, `public_tests/`, and `environment/`.
- Create or change implementation files only below `starter/`.
- Run tests and read-only diagnostics from the repository root.
- Add your own temporary test fixtures under a system temporary directory;
  clean them up through the test framework.

Do not inspect, search, copy, or change anything under `sealed/`. Do not edit
public tests to make an implementation pass. Do not add answers, reference
implementations, credentials, host files, or generated root filesystems to the
learner-visible tree.

## Commands

Use `PYTHONPATH=starter` from the repository root:

```bash
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
python3 environment/probe.py
python3 environment/probe.py --try-userns
```

The last command is optional and Linux-specific. It creates a short-lived user
namespace probe; it does not make the full runtime safe or supported.

## Implementation constraints

- Preserve the public names and signatures described in `REQUIREMENTS.md`.
- Use Python's standard library and deterministic behavior for the required
  stages.
- Keep validation, path resolution, plan construction, persistence, and
  execution coordination as separate concerns.
- Use parameterized data and argument-vector subprocess APIs. Never construct
  a shell command string and never use `shell=True`.
- Put a finite timeout on subprocesses, capture output, and start a separate
  process group when implementing the optional real backend.
- Never silently weaken requested isolation. Report an unavailable backend
  with the specified domain exception.
- Treat guest absolute paths as paths inside the configured rootfs, not as host
  absolute paths. Reject traversal and every symlink in an executable path.
- Make lifecycle transitions compare the persisted current state with the
  expected state atomically. Readers must not observe partial JSON.
- Keep clocks and execution backends injectable so unit tests do not depend on
  wall-clock timing or Linux namespace support.
- Preserve exception causes where useful, but do not place configuration
  contents, environment values, or unrelated host paths in error messages.

## Safety and test discipline

Unit tests should use temporary directories, synthetic files, fake clocks, and
fake backends. They must not require root, change the caller's namespaces, use
the host network, or execute untrusted payloads. Real `unshare` experiments
belong in explicitly opted-in integration work on disposable Linux systems.

Before finishing, run the public suite from the repository root. A passing
public suite is useful evidence, but it is not permission to inspect sealed
material and is not a claim of production-grade container isolation.
