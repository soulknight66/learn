# Review findings

1. Only children call `setpgid`. The first may exit before the second joins, and either child may pass `exec` before group placement is observed. The parent must call `setpgid(child, group)` after each fork and tolerate only the documented race outcomes.
2. A shell commonly ignores interactive signals. Both children inherit those dispositions and never restore defaults, so Ctrl-C or Ctrl-Z may not affect the job.
3. The parent waits only for the second child. The first can remain a zombie, and its resources/status are lost.
4. If the second `fork` fails, the first child continues and the pipe descriptors remain open; there is no group termination or reap path.
5. `exit` after failed `execvp` flushes copied stdio state and runs inherited handlers. The child should save `errno`, diagnose, and use `_exit(126/127)`.
6. There is no terminal transfer to the foreground group or restoration to the shell group.
7. Return handling collapses signaled termination to 125 instead of `128 + signal`.
8. Calls such as `dup2`, `close`, and `setpgid` have unchecked failures.

A sound protocol records every PID, designates the first PID as the group ID, and places each child from both sides of `fork`. Children reset signals, build descriptors, close originals, apply explicit redirections, and `execvp`. The parent closes descriptors immediately. Any later launch failure terminates the negative group ID and waits for every recorded child. For a foreground job it transfers the terminal, waits every member while preserving the last syntactic stage's status, and restores the terminal on every return path.
