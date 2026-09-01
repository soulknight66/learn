# Design questions

Write down your answers before implementing each stage, then revisit them after
the tests pass. This file intentionally provides questions without endorsed
answers.

## Configuration

1. Which inputs cross a trust boundary, and at what point should they become a
   normalized `ContainerSpec`?
2. What Python values resemble valid JSON values but should be rejected by a
   strict schema?
3. Should normalization retain references to the caller's lists and mappings?
   What failure could that create later?
4. Which validation error details help a learner diagnose a spec without
   leaking environment values or host paths?

## Executable resolution

5. In what coordinate system should `/bin/tool` be interpreted: host or guest?
6. How should a bare command differ from a command containing `/`?
7. What should empty, relative, repeated, or traversal-bearing PATH entries do?
8. At which path components can a symlink redirect lookup? What changes if an
   otherwise safe symlink is permitted?
9. Which filesystem changes could occur between validation and execution, and
   which of them are outside this exercise's guarantee?

## Isolation planning

10. Why should plan construction be pure and deterministic instead of probing
    `unshare` while building the object?
11. Which namespace requests depend on `network_mode`, and what security fact
    does `host` communicate?
12. What does mapping the caller to namespace root enable, and what does it not
    imply about host authority?
13. Why does a PID namespace commonly require a fork, and what obligations
    does its first process acquire?
14. Which isolation steps are still absent after all requested namespaces are
    successfully created?

## Lifecycle persistence

15. What invariant must hold if two workers concurrently expect `CREATED` and
    both request `RUNNING`?
16. Is an atomic file replacement sufficient to enforce that invariant? What
    other synchronization scope is relevant?
17. When should the clock be sampled, and which timestamps should survive a
    transition unchanged?
18. How should corrupt persisted JSON differ from a missing record?
19. What evidence should remain after an execution fails, times out, or is
    interrupted during state publication?

## Runtime boundary

20. What is the semantic difference between an `ExecutionResult` with exit
    code `1` and a backend exception?
21. Which backend behaviors should a fake be able to induce without invoking
    Linux facilities?
22. If recording `FAILED` itself encounters a state error, which exception and
    evidence should the caller receive?
23. Where should output decoding occur when a payload can emit arbitrary
    bytes?

## Optional Linux integration

24. What evidence is required before claiming that the requested namespaces
    are active, rather than merely present in an argument vector?
25. How will timeout cleanup reach descendants and avoid leaving a process
    behind?
26. How should the backend respond when one requested isolation feature is
    denied? Is degraded execution ever acceptable for this API?
27. Which additional mount, privilege, syscall, device, and resource controls
    would be required before considering hostile workloads?
28. What tests can run on every platform, and which experiments must be
    explicitly opt-in and environment-labelled?
