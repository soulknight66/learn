# Review PR: reduce queue claim latency

The proposed PR selects READY work before opening a write transaction, updates afterward, and
catches database errors to reduce caller noise. Write `REVIEW.md` with severity, concrete race
schedule, operational consequences, required changes, and tests. Look beyond the headline
throughput rationale. Run the sealed demonstration only after submitting your review.
