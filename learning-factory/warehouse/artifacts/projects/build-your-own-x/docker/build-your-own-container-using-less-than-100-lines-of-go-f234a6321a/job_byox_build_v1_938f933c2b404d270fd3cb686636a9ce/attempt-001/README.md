# Tinybox: build a small Linux container runner in Go

Tinybox is a progressively revealed systems-programming challenge. You will build a Linux-only
command runner that creates fresh namespaces, enters a chosen root filesystem, and replaces its
bootstrap process with a requested command. The project is intentionally small enough to study,
but it is not a security boundary and must not be used for hostile workloads.

This material was independently generated from catalog metadata for the topic “Build Your Own
Container Using Less than 100 Lines of Go.” It does not reproduce the linked article. There is no
line-count target: observable behavior, failure handling, and explicit limitations matter more.

## Learning path

1. Read [REQUIREMENTS.md](REQUIREMENTS.md) and [CONCEPTS.md](CONCEPTS.md).
2. Implement configuration validation in `starter/`.
3. Produce a deterministic launch plan and parent-to-child argument encoding.
4. Configure Linux namespace creation and optional user-ID mappings.
5. Implement child filesystem setup and final process execution.
6. Run the pure public tests after every step; run the opt-in integration check only in a disposable
   Linux VM where namespace creation is permitted.

The starter is deliberately incomplete but should compile once a Go 1.21+ toolchain is present.
Public tests exercise only deterministic behavior; they do not perform privileged operations.

```text
cd public_tests
go test ./...

cd ../starter
go build ./cmd/tinycontainer
```

To prepare the tiny static integration fixture, follow `environment/README.md`. A typical manual run
after completing the starter is:

```text
./tinycontainer run --rootfs /absolute/path/to/rootfs -- /bin/probe
```

Use a disposable VM. Even a correct exercise solution lacks cgroups, seccomp, capability dropping,
resource limits, image verification, and many other controls expected from a production runtime.

## Reveal boundary

Learner-facing files are this README, `AGENTS.md`, `MANIFEST.yaml`, `REQUIREMENTS.md`,
`CONCEPTS.md`, `DESIGN_QUESTIONS.md`, and the `starter/`, `public_tests/`, and `environment/`
trees. Reference material is sealed for independent evaluation.

## Artifact status

The artifact status is `GENERATED` + `PARTIAL`. The host used to generate it had no `go` executable,
so the Go implementation and tests could not be compiled here. Static structure, JSON identity,
shell syntax, credential scanning, and the C rootfs probe were checked as recorded in
`VALIDATION.md`. Independent validation remains required.
