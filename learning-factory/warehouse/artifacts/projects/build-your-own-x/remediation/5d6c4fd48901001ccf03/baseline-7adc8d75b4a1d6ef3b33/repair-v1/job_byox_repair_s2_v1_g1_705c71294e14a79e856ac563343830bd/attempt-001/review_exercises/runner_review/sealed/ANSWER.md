# Review answer

- Joining arguments and using `shell=True` turns metacharacters into code execution.
- Inheriting the entire host environment crosses secrets and behavior into the child.
- There is no timeout, new session/process group, or descendant cleanup strategy.
- Unbounded captured output can exhaust memory.
- Returning only a boolean discards exit code, stdout, stderr, and timeout evidence.
- Calling `subprocess.run` directly prevents a deterministic fake launcher test.

Use an immutable argv tuple; `shell=False`; a minimal explicit environment; binary stdin/stdout/stderr;
a bounded input and timeout; `start_new_session=True`; process-group cleanup and reap on timeout; a
structured result; and injected process/kill callables. Production additionally needs streamed,
bounded logs and a cgroup membership/kill boundary.
