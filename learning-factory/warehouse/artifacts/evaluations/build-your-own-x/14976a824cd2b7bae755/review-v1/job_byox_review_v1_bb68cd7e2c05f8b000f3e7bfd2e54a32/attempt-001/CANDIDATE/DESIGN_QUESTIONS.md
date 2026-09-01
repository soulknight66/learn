# Design questions

Write down your answers before implementing the corresponding phase. These prompts are intentionally
not accompanied by model answers. Revisit them after tests expose a mistaken assumption.

## State model

1. What facts are durable after every CLI process exits? Which facts are meaningful only while a run is
   active?
2. What invariant distinguishes a complete registration from a partially failed `create`?
3. How will a reader distinguish “no active run,” “the recorded process is alive,” and “the marker is
   stale”?
4. Why is a PID insufficient as a long-lived process identity? What Linux observation can strengthen it?
5. Which paths are derived from user input, and at what point is each input validated?
6. How can cleanup prove that its target is state owned by MiniCTR rather than the registered rootfs?
7. What permissions should the state root, registration directories, and metadata have under a typical
   multi-user umask?
8. How will you detect state/rootfs overlap before creating a requested state directory that does not
   exist yet, including through symlinked ancestors and `..` components?

## Transitions and concurrency

1. List the allowed transitions among missing, created, and running. What result should every other
   transition produce?
2. Which observations and writes must share one critical section for `run` versus `delete`?
3. How does your lock behave if its owner is killed? Is waiting bounded?
4. Can `ps` remain read-only while still recovering a stale run marker? If not, how will you document
   and serialize the recovery?
5. At what exact point does a run become visible as `RUNNING`, and at what point does it become
   `CREATED` again?
6. If the isolator cannot start, which operation owns removal of transient state?
7. What happens when two processes concurrently create the same name? How could you test the outcome
   repeatedly without accepting a flaky result?

## Argument and metadata safety

1. Where could an unquoted expansion perform word splitting or pathname expansion?
2. How will you preserve an empty final argument?
3. Why would serializing metadata as shell assignments create an execution vulnerability?
4. Can a rootfs path contain spaces, leading dashes, wildcard characters, or command-substitution
   punctuation in your representation?
5. Does any utility need a `--` delimiter before a caller-derived operand?
6. Is `MINICTR_ISOLATOR` treated as one executable path or as a configurable command string? What
   security and test consequences follow?

## Isolation sequence

1. What can a process still observe if you change only its root directory?
2. Which required namespaces can an unprivileged user create on your host, and how did you verify the
   result rather than just tool availability?
3. What must be true of the user namespace before mount and root-changing operations are attempted?
4. How will you prevent a mount made during setup from propagating to the host mount namespace?
5. Which PID namespace should the mounted proc filesystem represent?
6. Where is the working directory when the apparent root changes?
7. What environment variables should cross the isolation boundary? Which ones could reveal host
   details or alter loader/shell behavior?
8. If any required isolation step fails, is there a path that accidentally executes the user command
   without the boundary?

## Process behavior

1. Which process receives terminal-generated `SIGINT` when MiniCTR runs in the foreground?
2. How will the wrapper forward termination while still running cleanup exactly once?
3. What exit status should `run` return for a normal child exit, a setup failure, and a signal?
4. What happens to grandchildren after the requested command exits?
5. Who reaps orphaned children inside the PID namespace?
6. Does your active marker name the wrapper, isolation helper, or inner command? What are the tradeoffs
   for liveness checks and signal forwarding?

## Testing and evidence

1. Which requirements can a fake isolator establish conclusively?
2. Which claims require observing namespace identifiers, mount tables, process views, or network state?
3. How will you guarantee that a failed real-isolation test leaves no host mounts or processes behind?
4. What should a test do if the host explicitly forbids unprivileged user namespaces?
5. How can a test inject a command argument that would be dangerous only if it were re-parsed?
6. What evidence would justify “works on this host,” and what additional evidence would be needed for a
   security or production-readiness claim?

## Stretch design

1. Where would resource limits fit without coupling durable state to a particular cgroup version?
2. How would you introduce an init/reaper without changing the user’s command argv?
3. What new cleanup and ownership problems appear if multiple commands may run in one instance?
4. Which parts of this CLI contract could map to an OCI bundle, and which are deliberately incompatible?
