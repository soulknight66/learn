# Public tests

These tests import the starter through a local module replacement. They exercise parsing,
validation, round-tripping, and planning only. They never call `Run` or `RunChildInvocation`, so
running them does not create namespaces, mount filesystems, or change root.

```text
go test ./...
```

The initial starter is expected to fail. A passing result establishes the deterministic half of the
contract, not runtime isolation or production safety. Additional independent validation may test
documented requirements that are not enumerated here.
