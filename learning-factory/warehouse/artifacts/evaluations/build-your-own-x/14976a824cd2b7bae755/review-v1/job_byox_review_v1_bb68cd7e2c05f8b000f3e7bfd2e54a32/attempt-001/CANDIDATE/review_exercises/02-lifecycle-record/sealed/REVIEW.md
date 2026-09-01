# Model review

## High: the record has no exclusive owner

Every caller overwrites `run`. If A starts, B overwrites the file, and A exits,
A removes B's record. Creation and cleanup need per-instance coordination.
Cleanup should compare the complete value it created and remove it only while
holding that same coordination; it must never delete a successor's record.

## High: PID alone is not process identity

After a crash, a PID can be reused. `kill -0` would then classify an unrelated
process as the active run. On Linux, store both PID and the process start-time
token from `/proc/PID/stat`, then require both to match. Treat malformed,
missing, inaccessible, or mismatched records as stale according to a single
documented policy.

## High: traps have surprising scope

Function-installed traps replace the caller's traps and remain installed after
the function returns. The single-quoted body also relies on dynamically scoped
variables that may no longer have the intended value at shell exit. Save and
restore prior traps or run lifecycle management in a dedicated subprocess.
Signal handlers should arrange cleanup and then reproduce a meaningful signal
exit rather than continuing normally.

## High: child status is masked

The final successful `rm` becomes the function status, hiding isolation
failure. Capture the isolator's status immediately, perform owner-checked
cleanup, and return the captured status. Define how cleanup failure is
reported without turning a failed container command into apparent success.

## Medium: partial and malformed state is trusted

Redirection directly replaces the record without a temporary-file commit,
and readers do not validate field count or numeric shape. Use a restrictive
umask, write a complete record privately, atomically publish it, and parse it
strictly. Quote all local variables and declare them `local` so concurrent or
nested shell functions cannot mutate shared globals.
