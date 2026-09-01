# Review findings

## Blocking correctness

1. **Stages are launched sequentially.** The parent calls `waitpid` inside the
   creation loop. The producer can fill the pipe before a consumer exists and
   block forever. Launch every stage before entering the foreground wait phase.
   A regression test must transfer substantially more than pipe capacity.

2. **The parent retains pipe endpoints while waiting.** Even for a producer
   small enough not to fill the pipe, the next stage cannot be launched until
   the first exits, and closure is delayed until after the wait. Descriptor
   closure belongs immediately after the fork(s) that need a copied endpoint.

## Descriptor ownership

3. **Children keep original descriptors after `dup2`.** Every child inherits
   `previous_read` and both `next_pipe` ends, then executes without closing
   them. This can suppress EOF, keep extra references for the life of an
   external command, and leak descriptors into programs. After successful
   duplication, close every temporary pipe descriptor in every child.

4. **`pipe`/`fork` error paths leak.** A `pipe` failure abandons
   `previous_read`. A `fork` failure abandons `previous_read` and both newly
   created endpoints. Track all currently owned descriptors and close them on
   every return.

5. **Wait failure also leaks.** The early return on `waitpid` failure skips the
   same descriptors. `EINTR` should normally retry; terminal errors still need
   cleanup.

## Child and status handling

6. **The post-fork child calls `exit`.** `exit` flushes C stdio state copied
   from the parent and runs inherited exit handlers. The isolated child failure
   path should report with an appropriate low-level/controlled mechanism and
   finish via `_exit`.

7. **All `execvp` failures become 127.** A not-found command conventionally
   differs from a located command that cannot execute. Preserve `errno` and map
   the required cases to 127 or 126.

8. **Wait status is decoded without checking its kind.** `WEXITSTATUS(status)`
   is meaningful only if `WIFEXITED(status)` is true. Signal termination needs
   the project's `128 + signal` mapping. Interrupted/stopped statuses need the
   launcher's foreground-job policy.

9. **Zero commands returns a fabricated success.** With `command_count == 0`,
   `status` remains zero and happens to decode as exit zero. Reject the invalid
   call or document and test an explicit empty-pipeline result.

## Partial-launch semantics

10. **Already started children are orphaned on later failure.** Once launch is
    concurrent, a later `pipe` or `fork` may fail after earlier stages exist.
    The launcher needs a process list, a policy to terminate or let those
    children finish, closure of all channels, and a reap loop. Returning alone
    loses both children and status evidence.

A sound high-level shape is: validate the plan; create channels and fork all
stages while recording PIDs; establish each child's endpoints and close unused
copies; close all supervisor copies; then wait/reap by recorded PID and compute
status from the final stage. Job-control implementations add process-group
establishment to the launch phase.
