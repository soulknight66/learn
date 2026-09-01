# Novel check: pooled frame review

## Administration

Keep this check examiner-only until the learner's submission is frozen. Present only the prompt section, allow 20 minutes, prohibit network access and code changes, and capture the response as a separate examiner artifact. The learner may reason on paper or in a plain text response and may refer to their frozen submission.

This check samples near transfer to a new byte layout and operational context. Its existence is not evidence of transfer, and even a successful response applies only to this bounded evaluation.

## Prompt to present

A teammate proposes a higher-throughput revision that reuses frames from a pool. The revised frame has this layout:

```text
[0, 12)   request data
[12, 13)  role byte; admin is 0x01
[13, 15)  two-byte rate-limit bucket
[15, 19)  canary b"SAFE"
```

The proposed request sequence is:

```text
take one previously used frame from the pool
copy the entire payload from index 0
if payload length is greater than 12:
    write 0x00 only to the role byte
    return REJECT
decide access from the role byte
log the complete frame as hexadecimal
return the frame to the pool
```

Without running or changing code, respond to all of the following:

1. Identify the first payload length that can reach the role, each byte of the rate-limit bucket, and the canary. Explain your index reasoning.
2. Identify at least four distinct security or operational defects in the sequence. Tie each defect to a threatened property rather than merely calling the code unsafe.
3. Give a corrected sequence of validation, initialization, copying, decision, diagnostic recording, and pool return. State what must happen on every rejection and exception path.
4. Propose three focused tests that would distinguish the corrected design from the proposal, including one cross-request test and one diagnostic-privacy test.
5. State whether checking the canary immediately before pool return is a prevention, detection, or recovery mechanism, and bound the claim.

## Examiner landmarks and scoring (15 points)

### Offset transfer — 3 points

The response derives boundaries from half-open ranges: length 13 can first write index 12 (role), length 14 reaches index 13 (first bucket byte), length 15 reaches index 14 (second bucket byte), and length 16 reaches index 15 (first canary byte). Award partial credit for correct reasoning with one arithmetic slip.

### Defect analysis — 4 points

Strong responses distinguish at least four of these:

- validation occurs after corruption, so rejection is not atomic;
- repairing only the role leaves bucket or canary corruption behind;
- a pooled frame is not freshly initialized, so old role, data, or metadata can cross request boundaries;
- exception paths may return dirty state or lose the frame unless cleanup is explicit;
- complete-frame logging exposes request data and adjacent metadata;
- a decision could observe stale state even for a short payload that does not overwrite the role;
- a canary check after a decision cannot retroactively prevent misuse.

Require a property connection such as authorization integrity, rate-limit integrity, request isolation, availability, or diagnostic privacy.

### Corrected lifecycle — 4 points

Full credit requires: validate type and length before taking or mutating a frame where practical; initialize every region on checkout; copy only validated data; decide from initialized metadata; emit content-free diagnostics; and use guaranteed cleanup that clears or discards the frame on all returns and exceptions. Accept a design that takes a frame before validation only if it guarantees no mutation and safe cleanup.

### Discriminating tests and canary claim — 4 points

Tests should assert state, not just response codes. Expected coverage includes reuse after an authorization-changing or rejected request, proof that rejection preserves or discards the complete frame rather than repairing one byte, and proof that diagnostics contain no frame or payload representation. The canary is detection only for writes that actually change its bytes; it neither detects corruption confined to earlier metadata nor prevents a decision already made.

## Recording boundary

Record the prompt version, elapsed conditions, learner response hash, awarded points, and concrete observations. Do not infer broad memory-safety skill or course completion from this single near-transfer sample.
