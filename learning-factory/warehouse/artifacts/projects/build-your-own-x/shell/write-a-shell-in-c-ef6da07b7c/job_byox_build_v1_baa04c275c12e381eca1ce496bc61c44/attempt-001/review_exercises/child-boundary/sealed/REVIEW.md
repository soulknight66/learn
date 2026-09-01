# Canonical review findings

1. The child inherits ignored interactive signals. It must restore default dispositions for at least `SIGINT`, `SIGQUIT`, `SIGTSTP`, `SIGTTIN`, and `SIGTTOU` before exec. Otherwise Ctrl-C/Ctrl-Z may not affect the command.
2. Only the parent calls `setpgid`. The child can exec or exit before the parent call, producing `EACCES`/`ESRCH` and a job outside the intended group. Both sides should attempt group assignment around the fork race.
3. Unexpected `setpgid` failure merely prints and returns the child as usable. Terminal signal routing is then untrustworthy. The parent needs transactional termination/reaping or another explicit failure policy.
4. Diagnostics use standard output. In a pipeline they contaminate command data and may be consumed by the next stage. Diagnostics belong on standard error.
5. `execvp` failure always exits 1. The contract distinguishes not found (127) from other exec failure (126), and `errno` must be saved before formatting.
6. The child calls `exit` after fork. `exit` can flush inherited stdio buffers and run parent-configured handlers twice. The child failure path should use `_exit`.
7. Formatted stdio and `strerror` in a forked child are unsafe if the parent ever becomes multithreaded. This exercise's current shell is single-threaded, but a production boundary should prefer an async-signal-safe write strategy or `posix_spawnp`.
8. Parent errors are reported with `printf`, again to standard output, and the caller receives no indication that group setup failed.
9. There is no child-side terminal descriptor setup or close-on-exec policy shown. In a pipeline, inherited unused endpoints would prevent EOF or leak into the executed program.
10. No terminal handoff occurs. Even a correct group will not receive interactive input/signals until the parent assigns it with `tcsetpgrp`.

Bounded regression tests include a PTY Ctrl-C test, a helper that prints PID/PGID, a nonexistent executable status check, a permission-denied status check, and a pipeline that asserts stderr diagnostics never enter stdout.
