# Self-Check Questions

Use these questions to challenge your own evidence before preserving the submission.

## Authority and time

1. At the exact expiry tick, which component makes the authoritative decision, and what concrete trace demonstrates the boundary?
2. Can a denied grant consume an epoch, change either object, or create a misleading fence-install log in your implementation?
3. What happens if a caller presents the installed epoch with the wrong owner, or invents an epoch larger than the installed one?
4. Which single model action prevents a newly granted dispatcher from racing an incompletely installed fence?

## Identity and mutation

5. Does your logical payload exclude authority metadata while still detecting a genuine command-ID conflict?
6. What observable difference separates a fenced first attempt from a replay of an already accepted request through a stale dispatcher?
7. For every response path, can you point to evidence showing whether job state and request history changed?
8. Could a nonmutating business response change on retry after the job changes for another reason?

## Determinism and debugging

9. If two events have the same tick, where is their order defined and asserted?
10. Can every incident hypothesis be replayed from a clean process with one documented command?
11. Do log records expose both presented and active authority without requiring a reader to infer them from free-form text?
12. Would removing the log collector leave all responses and state transitions unchanged?

## Claim boundaries

13. Which failures are excluded by the single-process logical-time model?
14. What additional mechanisms and evidence would be needed before making claims about real clocks, coordinator failover, durable storage, or concurrent processes?
15. Does any sentence imply that the catalog locator was retrieved, that this is official course material, or that completing it earns course credit?
16. Are failed experiments and unresolved limitations preserved rather than summarized away?
