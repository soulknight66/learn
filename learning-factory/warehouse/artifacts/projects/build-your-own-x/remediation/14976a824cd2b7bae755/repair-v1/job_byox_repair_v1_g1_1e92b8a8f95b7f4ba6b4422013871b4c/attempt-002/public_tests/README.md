# Public tests

`test_minictr.sh` is a self-contained Bash test runner for the observable MiniCTR control-plane
contract. It uses only disposable directories below the system temporary directory and invokes every
CLI process through a bounded `timeout`.

Run it from the repository root:

```bash
bash public_tests/test_minictr.sh
```

To test another executable:

```bash
MINICTR_BIN=/absolute/path/to/minictr bash public_tests/test_minictr.sh
```

The executable path must be directly executable. The runner supplies a fresh absolute `MINICTR_HOME`
and sets `MINICTR_ISOLATOR` to `fakes/isolate_capture.sh`.

## What the suite covers

The nine cases check:

- help, unknown-operation handling, and absence of state side effects;
- locale-independent ASCII name, rootfs, and state-root validation;
- rejection of overlapping state and rootfs trees before mutation;
- create/duplicate/ps/delete behavior without a running process;
- exact TSV schema and bytewise name ordering;
- preservation of spaces, globs, punctuation, a shell-looking argument, and an empty argv element;
- transparent child stdout, stderr, nonzero status, and post-run cleanup;
- visible `RUNNING` state plus delete/second-run exclusion; and
- a start-gated duplicate create with exactly one winner.

The runner emits TAP version 13. A case can contain several related assertions and stops at its first
failed assertion, while later cases continue. Diagnostics beginning with `#` explain the mismatch.

## Fake-isolator protocol

The fake accepts the same public seam as the real isolator:

```text
isolate_capture.sh ROOTFS COMMAND [ARG...]
```

It does not execute `COMMAND`. Test-only environment variables let the runner observe behavior:

| Variable | Fake behavior |
| --- | --- |
| `MINICTR_FAKE_CAPTURE` | write rootfs and command argv as NUL-delimited fields |
| `MINICTR_FAKE_STDOUT` | print one stdout line |
| `MINICTR_FAKE_STDERR` | print one stderr line |
| `MINICTR_FAKE_STATUS` | return the selected status in the range 0–255 |
| `MINICTR_FAKE_READY` | create a marker immediately before an optional pause |
| `MINICTR_FAKE_RELEASE` | wait, for a bounded interval, until this path exists |

These variables are not part of the MiniCTR runtime interface. Runtime code should neither parse nor
special-case them; ordinary environment inheritance is enough for the fake.

The separate `fakes/start_gate.sh` is an invocation barrier for the duplicate-create case. Both CLI
processes must reach it before either candidate is launched. It does not expose or assume the
candidate's private state layout.

## What the suite does not prove

No public test invokes `unshare`, `mount`, `chroot`, `sudo`, the network, or a command from a real rootfs.
Consequently, a passing result does not prove:

- any Linux namespace was created;
- mount propagation or proc setup is correct;
- a user-ID mapping is safe;
- signals reach a PID-namespace process tree;
- a hostile rootfs is contained; or
- the runtime has production-grade security.

Those properties need explicit integration tests on a suitable disposable Linux host. Keep their
results separate from the deterministic public suite.

## Expected starter result

The supplied starter passes parsing and validation cases but deliberately reports `TODO` for runtime
operations. A nonzero suite status is expected before learner implementation. Do not change the fake or
the assertions to hide those failures.
