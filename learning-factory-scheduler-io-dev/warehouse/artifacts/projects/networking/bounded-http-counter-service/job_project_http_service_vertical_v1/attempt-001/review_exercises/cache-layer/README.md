# PR review: “Cache GET responses to reduce handler latency”

The proposed patch adds a small wrapper intended to cache successful GET responses. Review it
as if it were headed toward an authenticated counter/account service. Write `REVIEW.md` with
location, severity, concrete failure scenario, and suggested direction. Consider correctness,
security boundaries, concurrency, resource limits, latency, invalidation, observability, and
lifecycle. Avoid generic style comments unless they obscure a real invariant.

The patch is syntactically valid and its headline happy path works. A sealed executable
demonstration and expected review are available after submission.
