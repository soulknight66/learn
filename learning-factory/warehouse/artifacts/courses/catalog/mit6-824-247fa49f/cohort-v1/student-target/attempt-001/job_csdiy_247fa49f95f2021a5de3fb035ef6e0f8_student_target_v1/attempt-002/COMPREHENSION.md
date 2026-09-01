# Comprehension Prompts

Answer all seven prompts in the comprehension section of `submission.md`.
Label them `C1` through `C7`. Aim for 80–160 words each, and point to a
specific invariant, trace row, or proposed test when the prompt asks about your
design. These are questions, not additional facts about an official course.

## C1 — What did the timeout reveal?

A client sends an `Append` and receives no reply before its deadline. Compare
at least two network histories consistent with that observation. What may the
client safely report to its caller at that moment, and what would be an
overclaim?

## C2 — What makes an operation the same operation?

Explain why `seq` alone is not a system-wide request identity. State how your
design distinguishes an exact retry, a different client's request with the same
sequence number, and conflicting reuse by the original client. What state must
remain isolated?

## C3 — Safety, liveness, and assumptions

Choose two central claims from your contract. Classify each as safety, liveness,
or an environmental assumption and defend the classification. For any liveness
claim, list the minimum progress assumptions it needs under the given model.

## C4 — How much history is enough?

Consider T2 and a policy that remembers only the most recent request per client.
Does that policy satisfy your stable-response and at-most-once contract for every
allowed delayed delivery? Give a concrete trace-based argument. Then explain the
cost or protocol assumption associated with your chosen alternative.

## C5 — Is a repeated read a new read?

In T3, relate the second delivery of `Get(B, 1, "x")` to logical-operation
identity and client-visible history. Contrast handling it as the original
logical operation with handling it as a fresh observation. Which of your named
requirements decides the behavior?

## C6 — What changes at restart?

Use boundary probe B1 to explain which volatile facts disappear and which
guarantee can no longer be established. Describe one concrete persistence or
session mechanism that could change the answer, including the atomic relationship
it must have with the key/value mutation. State what remains unproved.

## C7 — Why is this not consensus?

The server transition function can be deterministic for an already ordered event
stream. Explain why that does not make several servers agree on one order when
messages and processes fail. Identify two additional distributed-system
questions intentionally absent from this kickoff and one piece of future
evidence each would require.
