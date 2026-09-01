# Starter module

This module declares the complete API for the Tinybox runner but leaves the challenge operations in
`api.go` unimplemented. Start with the functions that do not cross a privilege boundary.

Suggested checkpoints:

1. `ValidateConfig`
2. `ParseRunArgs`, `EncodeChildArgs`, and `ParseChildArgs`
3. `NamespaceFlags` and `BuildLaunchPlan`
4. `Run`
5. `RunChildInvocation`

`cmd/tinycontainer/main.go` is a ready-made thin CLI. Do not move runtime logic into it; keeping the
library testable is part of the exercise.

Run the external tests from their own module:

```text
cd ../public_tests
go test ./...
```

The namespace and filesystem steps are Linux-specific. Keep non-Linux behavior explicit and do not
attempt integration runs on a development workstation that contains valuable mounts or data.
