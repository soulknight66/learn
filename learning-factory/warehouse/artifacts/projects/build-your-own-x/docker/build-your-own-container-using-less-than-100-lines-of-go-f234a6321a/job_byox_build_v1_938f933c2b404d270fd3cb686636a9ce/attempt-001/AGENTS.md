# Learner agent guide

Work only in `starter/` unless a task explicitly asks you to add a learner-visible test in
`public_tests/`. Treat `sealed/` and the non-learner exercise trees as unavailable answer material.

Preserve these constraints:

- Keep the module dependency-free; use the Go standard library.
- Keep deterministic planning separate from namespace and mount side effects.
- Never execute mount or namespace operations from unit tests.
- Use `exec.CommandContext`/`exec.Command` argument slices, not shell command strings.
- Validate the rootfs before changing namespaces and again in the child.
- Never accept `/` as a rootfs, and never recursively remove a supplied rootfs.
- Preserve the contained command's exit code.
- Return contextual errors; do not claim isolation if any required setup operation failed.
- Do not weaken tests or copy a reference implementation.

Run commands from the module that owns them:

```text
cd public_tests && go test ./...
cd ../starter && go vet ./... && go build ./cmd/tinycontainer
```

The integration fixture is opt-in and should be used only on disposable Linux hosts. Passing unit
tests does not establish that the runner is safe for untrusted programs.
