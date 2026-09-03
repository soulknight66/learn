# Sealed design answers

## Interface decisions

Stable records (`list`, `inspect`, and successful mutation names) go to stdout; usage and operational
failures go to stderr. `run` forwards the selected runner's streams because the controller is not a
log protocol. The literal `--` makes the boundary between controller operands and container argv
unambiguous. The controller returns the runner's exact status so scripts can treat Tinybox like the
process they requested.

## Safe path construction

Names are accepted only after the complete anchored grammar matches. Every container target is then
constructed as the fixed canonical `containers_dir` prefix plus that name. Deletion repeats the
exact-string boundary check and rejects symlinked container directories before `rm -rf`.

Creation copies `source/.` into a new `rootfs/`, which copies contents rather than nesting the source
basename. It builds beneath the state filesystem's `tmp/`, so final `mv -T` is a same-filesystem
atomic publication. A failed copy leaves no published container, and the exit trap removes only a
scratch path proven to be below `tmp/`.

This is protection against CLI mistakes and ordinary tampering, not a defense against another host
process with write access to the state tree. Private permissions reduce that exposure.

## State protocol

Atomic `mkdir locks/NAME.lock` elects one cooperating mutator. Ordinary command entry points fail
immediately on an existing lock. Create holds it through publication. Run holds it while checking and
changing state, then releases it while waiting; the `RUNNING` state excludes a second run or deletion
without holding a lock for an arbitrary duration. After the runner returns, completion retries lock
acquisition for a finite interval so a transient competing metadata check cannot strand `RUNNING`.

Status replacement writes a complete adjacent temporary regular file and renames it. On completion,
`exit_code` is published before `EXITED`, making the final status the commit marker. There is still a
small observable multi-file window and no recovery after `SIGKILL` or host failure. A production
design would use a transactional store plus lease/reconciliation logic.

No metadata is evaluated. The reader accepts exactly one line, recognizes only lifecycle constants,
and separately validates an exit code in `[0,255]`.

## Argument preservation

After shifting controller operands, `"$@"` remains the authoritative command vector. Both controller
and runner pass it in double quotes. No layer flattens or reparses it. Thus whitespace, glob
characters, semicolons, and empty non-command arguments remain data.

## Namespace staging

The runner needs host tools to set the hostname and mount `/proc` before changing root. Rather than
using `sh -c`, it re-executes its own absolute path as PID 1 in the requested user, mount, PID, UTS,
and IPC namespaces. A per-process token prevents an accidental direct call from being mistaken for
the internal stage.

The inner stage makes mount propagation private, changes the UTS hostname, mounts a proc filesystem
from inside the new PID namespace, and finally uses the already-available host `chroot` binary to
change root and working directory before `exec` of the original argv.

The command becomes PID 1 and must handle that role. The backend intentionally omits networking,
cgroups, capability minimization, seccomp, device policy, and robust init/reaping.

## Test strategy

Controller tests inject an executable runner. The public double records argv and returns a chosen
status. The sealed controlled runner can block on explicit files, allowing the suite to observe
`RUNNING` and exercise exclusion deterministically. A completion-contention schedule also holds the
name lock in a competing deletion while releasing the runner, then verifies the runner's status is
durably committed after that competitor rejects `RUNNING`. Two simultaneous create processes test
the atomic name claim. A separate environment probe reports whether the host permits user namespaces;
it is not conflated with the portable suite.
