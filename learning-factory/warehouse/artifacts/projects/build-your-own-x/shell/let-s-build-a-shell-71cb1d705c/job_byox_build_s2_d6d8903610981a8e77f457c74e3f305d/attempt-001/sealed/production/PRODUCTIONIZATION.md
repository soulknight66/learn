# Productionization assessment

Status: **not productionized**.

The reference demonstrates the exercise contract and has deterministic
black-box coverage. Promotion would require work beyond the authorized scope:

1. Replace fatal allocators with recoverable errors and verify every restore
   path under injected failures.
2. Save and restore shell and per-job terminal modes, including stopped jobs.
3. Define logout, `SIGHUP`, orphan, `disown`, and background-stdin policy.
4. Replace polling around `getline` with an event-aware input/reaping design.
5. Add hard resource ceilings for tokens, argv bytes, processes, and open
   descriptors before allocating or forking.
6. Add sanitizer and fault-injection jobs on several POSIX implementations.
7. Audit PATH execution and inherited environment/file descriptors for an
   explicit threat model.
8. Specify locale, Unicode/byte handling, diagnostic stability, and terminal
   capability behavior.
9. Establish versioning, packaging, supported platforms, and a security
   response process.

No production-readiness or portability claim is made by this artifact.
