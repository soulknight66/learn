# Meta-evaluation 003 — scale-out publication gate

Date: 2026-08-30

Scope: independent adversarial review of the allocator, Sprig language/bytecode VM,
and durable event-service generators before their first scheduled publication.

## Allocator findings and corrections

The initial candidate misclassified some stale frees after coalescing, accepted forged
segregated-bin topology, exercised sanitizers only for one architecture, called a
single-seed model check general fuzzing, and used casted declared character arrays in a
way that can violate C11 effective-type rules.

The gated revision now validates physical topology before dereferencing bin nodes and
requires exact-one bin membership, rejects overlapping state/arena storage, defines
represented double-free versus stale invalid-pointer behavior, and uses dynamically
allocated suitably aligned storage in every authoritative fixture. The learner contract
explicitly teaches why a casted declared `unsigned char[]` is outside the portable
contract. All three architectures run 4,000-operation constrained-arena models that
must observe failed resize atomicity. Unsupported `FUZZED` and `SANITIZED` claims were
removed; this host records sanitizer execution as unavailable because its linker lacks
the required runtimes. The final pack exposes 24 validators and remains `PARTIAL`.

## Language/VM findings and corrections

The initial tree-walk and bytecode engines differed in binding-error order and step
budgets. The lexer accepted Unicode outside its documented ASCII grammar, large numbers
could leak Python exceptions, signed 64-bit minimum was rejected, and malformed bytecode
could bypass operand/opcode checks. Its first benchmark also mixed compilation with
dispatch while discussing dispatch cost.

The gated revision uses ASCII tokens and bounded typed integer parsing, handles
`INT64_MIN`, aligns semantic step accounting and error order, and verifies bytecode
opcodes, operand types/arity, control-flow reachability, and stack height before execution.
Its benchmark is explicitly end-to-end, including compilation. A novel independent probe
ran 440 valid/error/budget cases across both engines with zero mismatches; a second seed
passed 500/500 stateful differential cases. The final pack exposes 20 validators and
keeps recursion and hostile-input memory limits under `PARTIAL`.

## Event-service findings and corrections

The initial service had no claim token. A stale attempt reclaimed by the same owner could
acknowledge a newer lease; expired release was accepted; heartbeat could shorten expiry;
repeated lease crashes bypassed `max_attempts`; and a sequential dispatcher prefetched
leases it did not heartbeat. Validator reruns also failed after measured output existed.

The gated revision persists a random per-claim fencing token and requires live
owner/token/lease checks for heartbeat, effect, acknowledgement, failure, and release.
Heartbeats cannot shorten leases, exhausted expired claims enter the dead-letter queue
atomically, and the dispatcher claims on demand. DLQ history and cursors survive requeue,
the benchmark writes atomically with timestamp/hash, crash validation uses a real child
process, bug reproduction requires its unique exit code, and the complete validator set
passes twice on the same workspace. The final pack exposes 18 validators and remains
`PARTIAL`.

## Gate decision

All three generators and their new regressions pass in the integrated 105-test factory
suite. They are eligible for scheduled external validation, but this report is not the
publication evidence: the controller must still run every returned validator, checksum
the exact resulting tree, and archive only a fenced successful attempt.
