# Sealed reference implementation

This is an independently generated reference for the declared Tinybox API. It uses only the Go
standard library. Pure operations live apart from Linux syscall code, and child setup errors travel
over a close-on-exec pipe so they cannot be confused with workload exit status 125.

Build from this directory with Go 1.21 or newer:

```text
go build ./cmd/tinycontainer
```

Reference tests are intentionally a separate module at `../reference_tests`. Namespace integration
is skipped unless an operator supplies `TINYCONTAINER_INTEGRATION_ROOTFS` on a disposable Linux host.

This code is educational. Its known security and lifecycle gaps are documented in
`../production/PRODUCTIONIZATION.md` and `../REVIEW.md`; it is not an OCI runtime or a production
sandbox.
