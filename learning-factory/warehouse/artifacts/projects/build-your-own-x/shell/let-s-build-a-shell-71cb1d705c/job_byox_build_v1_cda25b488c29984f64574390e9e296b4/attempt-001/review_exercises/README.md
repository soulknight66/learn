# Code-review exercises

These exercises ask for a review, not a wholesale rewrite. Each directory has a
standalone, compilable C program and a review brief. The programs intentionally
contain several defects representative of shell implementations.

- [`pipeline_launcher`](pipeline_launcher/) examines launch order, descriptor
  lifetime, wait-status handling, and partial failure.
- [`job_table`](job_table/) examines `SIGCHLD`, job-table ownership, and lost
  wakeups.

For each finding, record:

1. the smallest relevant line or control-flow region;
2. the violated invariant;
3. a concrete failure scenario;
4. severity (`blocking`, `incorrect result`, `resource leak`, or `hardening`);
5. a repair direction and a regression test.

Prioritize root causes. Several visible symptoms may come from one ownership or
ordering error, while a cleanup fix may still be required independently.
