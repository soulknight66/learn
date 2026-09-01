# Sealed reference tests

These deterministic tests are validator material. They cover seven groups: scheduler timing and
quanta, lifecycle capacity and reaping, callback reentrancy and task identity, virtual memory
atomicity/reclamation, filesystem boundaries and aliasing, `ENOSPC` failure atomicity, and
fixed-resource exhaustion/reuse.

They compile the sealed C implementation directly with strict warnings. `SANITIZE=1` adds Address
Sanitizer and UndefinedBehaviorSanitizer when supported by the host compiler.
