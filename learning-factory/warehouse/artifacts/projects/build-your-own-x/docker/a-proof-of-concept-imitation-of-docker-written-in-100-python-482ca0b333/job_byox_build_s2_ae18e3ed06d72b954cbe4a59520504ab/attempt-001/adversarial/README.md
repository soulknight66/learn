# Adversarial exercise index

Instructor-gated prompt; no answers are stored here.

Design a tar corpus that probes normalization aliases, absolute paths, parent traversal, link types,
device/FIFO headers, duplicate members, file/directory ancestor conflicts, malformed payload lengths,
whiteout order, opaque directories, quota boundaries, and compressed expansion. For each case, state:

- whether rejection must happen before mutation;
- which exception family should be observable;
- what filesystem evidence proves no escape or partial publication occurred; and
- whether the case tests archive safety, process confinement, or both.

Then design a two-process race for `claim_start` and a crash point immediately after the claim commit.
Do not run hostile payloads or elevate privileges. Evaluator guidance is sealed separately.
