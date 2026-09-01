# Diagnosis

`wait(&status)` is equivalent to waiting for any eligible child. It returns the
background PID because that child exits first, but the program labels its exit
code 7 as the foreground result. A wait status has meaning only together with
the PID returned by `wait`/`waitpid`.

The focused repair is to call `waitpid(foreground, &status, 0)` for this
single-process foreground job, then reap `background` separately. A real shell
also needs a table keyed by PID (and grouped by process-group/job ID), because a
general `SIGCHLD` reaper may collect the status before foreground-control code
asks for it. Reaping must store the event rather than discard it or attribute it
to the currently interesting job.

Changing sleep durations only changes which schedule exposes the bug. Assuming
completion order matches launch order has the same flaw. `fixed.c` deliberately
keeps the background child faster while selecting the foreground PID.
