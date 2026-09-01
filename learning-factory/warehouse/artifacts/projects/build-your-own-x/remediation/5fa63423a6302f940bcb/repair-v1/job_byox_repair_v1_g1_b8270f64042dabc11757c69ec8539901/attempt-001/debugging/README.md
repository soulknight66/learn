# Debugging lab

These small programs isolate failures that often hide inside a shell. They are
intentionally incorrect and are not linked into `byosh`.

Work each exercise from observations first:

1. compile with `cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror`;
2. predict the process and descriptor state;
3. run potentially hanging examples only under a timeout or disposable test
   harness;
4. collect evidence with tools available on your system (`strace`, `ps`, and
   `/proc` are optional, not assumed by the exercise);
5. state the smallest repair and the general invariant that repair enforces.

The examples are:

- `exercise_01_pipe_eof`: output appears, but a pipeline never finishes;
- `exercise_02_wait_status`: a child exits, but the shell reports the wrong
  command status;
- `exercise_03_sigchld_race`: a very short background job can remain recorded
  as running forever.

Each exercise has its own sealed answer directory. Do not open it until you have
a diagnosis, a proposed patch, and one regression test.

