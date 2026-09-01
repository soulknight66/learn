# Exercise: review a payload runner

Review this intentionally reduced pseudocode; do not execute it:

```text
command = " ".join(spec.argv)
child = launch(command, use_shell=true, environment=caller_environment, capture_all_output=true)
stdout, stderr = child.wait_for_output()
database.set_state(container_id, "EXITED")
```

Identify issues involving input interpretation, environment boundaries, hangs, memory, descendants, lifecycle races, launch failures, and exit semantics. Recommend testable changes and state what still would not prove container isolation.
