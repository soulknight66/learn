# Reference design answers

MiniBox separates four boundaries: pure configuration, untrusted archive input, durable lifecycle state, and the host-dependent runtime backend.

Archive metadata is fully scanned before payload writes. This prevents an attack placed late in the tar from leaving earlier payload files behind. The destination path is checked component by component with `lstat`; links are rejected rather than resolved. Extraction still is not transactionally rollback-safe against disk errors, and concurrent mutation of the rootfs is outside the proof-of-concept threat model.

SQLite is the lifecycle authority. Python rejects bad transitions early, while a transition table and trigger prevent forbidden updates through another code path. `BEGIN IMMEDIATE` serializes contenders before they read the state. The caller supplies an expected state, so a stale runner loses rather than launching a second payload.

An ordinary nonzero payload exit is recorded as `EXITED`, because the runtime successfully started and observed the process. `FAILED` means the backend could not launch or the harness terminated it on timeout. Events retain this distinction.

The namespace backend only builds an immutable argv plan. `unshare --fork` is necessary for the child to enter the new PID namespace. `--root` and `--wd` establish the filesystem view and working directory without a shell. Rootfs contents, user-namespace policy, and other kernel controls remain external preconditions.

Runner passes a small baseline environment plus explicitly requested variables, never the caller's entire environment. Reader threads continuously drain stdout and stderr but retain at most the configured limit per stream. A new session makes timeout termination address the process group.

Image import uses per-ID advisory locks, private staging directories, and rename publication. Container rootfs copies are likewise staged. Cross-resource atomicity between SQLite and the filesystem is not complete; owned paths are cleaned on known failure, and production recovery would need a durable operation journal.
