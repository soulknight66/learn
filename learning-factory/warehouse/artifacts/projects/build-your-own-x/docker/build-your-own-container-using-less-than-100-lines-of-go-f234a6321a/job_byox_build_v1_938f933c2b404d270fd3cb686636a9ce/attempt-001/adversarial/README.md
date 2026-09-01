# Adversarial validation tier

This harness-facing module probes malformed boundaries that are easy to miss in a compact public
suite. It imports only the sealed reference and performs no namespace or mount operation.

```text
go test ./...
```

These cases are evidence about parser and validator behavior only. They are not penetration tests or
proof that a Linux container boundary resists hostile code.
