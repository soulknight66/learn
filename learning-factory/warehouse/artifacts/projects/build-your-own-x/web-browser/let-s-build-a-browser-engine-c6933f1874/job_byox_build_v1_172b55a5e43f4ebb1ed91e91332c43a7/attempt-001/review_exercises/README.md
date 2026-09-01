# Code-review reveal: transport budget

Exercise ID: `transport_budget`.

Review this orchestration logic:

```rust
let maximum = limits.max_header_bytes + 4 + limits.max_body_bytes;
let bytes = transport.exchange(&url, &request, maximum)?;
let response = parse_response(&bytes, &limits)?;
```

Produce a severity-ranked review. Consider integer behavior, whether the transport is trusted to honor its argument, call count, parsing order, response status/content type policy, and what a real connector would need to do about DNS and private addresses.

The validator answer is isolated under `sealed/review_exercises/transport_budget/sealed/`.
